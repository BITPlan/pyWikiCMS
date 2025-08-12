"""
Created on 2025-06-15
based on original tsite bash script
Tools to transfer a mediawiki site from one server to another
to e.g. migrate the LAMP stack elements or move from a farm based
to a dockerized environment

@author: wf
"""

from argparse import ArgumentParser
from dataclasses import dataclass, field
from datetime import datetime
import subprocess
import sys
from typing import Iterator, List, Iterable, TypeVar

from backend.remote import Remote
from backend.server import Server, Servers
from backend.site import Site, WikiSite
from backend.sql_backup import SqlBackup
from basemkit.base_cmd import BaseCmd
from basemkit.persistent_log import Log
from frontend.version import Version
from tqdm import tqdm
from wikibot3rd.smw import SMWClient
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.wikiuser import WikiUser


# enable generic types
T = TypeVar("T")

class Checks:

    @classmethod
    def check_age(cls,remote:Remote,filepath:str,days:float=1.0)->float:
        stats = remote.get_file_stats(filepath)
        age=None
        if stats:
            age=stats.age_days
            ok=stats.age_days <= days
            age_marker = "✅" if ok else "❌"
            print(
                f"{remote.host}:{filepath} {stats.age_days:.2f} d {age_marker}"
            )
        return age

@dataclass
class TransferTask:
    wiki_site: WikiSite
    source: Server
    target: Server
    debug: bool = False
    force: bool = False
    update: bool= False,
    progress: bool = True
    use_git: bool=False
    query_division: int = 50
    # Non-persistent calculated fields
    log: Log = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self.wikiUser = WikiUser.ofWikiId(self.wiki_site.wikiId, lenient=True)
        self.wikiClient = WikiClient.ofWikiUser(self.wikiUser)
        self.smwClient = SMWClient(
            self.wikiClient.getSite(),
            showProgress=self.progress,
            queryDivision=self.query_division,
            debug=self.debug,
        )
        self.site = self.wikiClient.get_site()

    def login(self):
        """
        login to the source wiki
        """
        wu = self.wikiUser
        # self.wikiClient.login()
        # just fake a compatible version to allow client login
        self.site.version = (1, 35, 5)
        self.site.clientlogin(username=wu.user, password=wu.get_password())
        pass

    def git_target(self, target_path: str) -> subprocess.CompletedProcess:
        """
        Handle git initialization and commit workflow for target path

        Args:
            target_path: Path to work in for git operations
        """
        remote=self.target.remote
        remote.log.do_log=self.debug
        git_dir = f"{target_path}/.git"
        git_stats = remote.get_file_stats(git_dir)

        if git_stats is None or not git_stats.is_directory:
            self.log.log("❌", "git", "git not initialized yet")

            git_cmds = {
                'init': f'cd {target_path} && git init',
                'add': f'cd {target_path} && git add *'
            }
            proc = remote.run_cmds_as_single_cmd(git_cmds)
            if proc.returncode != 0:
                return proc
        else:
            self.log.log("✅", "git", "git initialized")

        timestamp = datetime.now().strftime("%Y-%m-%d-%H_%M_%S")
        commit_cmd = f"cd {target_path} && git commit -a -m 'tsite commit at {timestamp}'"
        proc = remote.run(commit_cmd)
        # Git returns 1 when nothing to commit - this is not an error
        is_nothing_to_commit = proc.returncode == 1 and "nothing to commit" in proc.stdout
        success = proc.returncode == 0 or is_nothing_to_commit
        # fix return code for downstream
        if is_nothing_to_commit: proc.returncode=0
        status = "✅" if success else "❌"
        message = "nothing to commit" if is_nothing_to_commit else f"commit changes at {timestamp}"
        self.log.log(status, "git", message)

        return proc

    def check_ssh(self)->bool:
        """
        check the target site is available via ssh
        """
        avail=self.target.remote.avail_check() is not None
        return avail

    def check_site_sync(self)->bool:
        """
        check the site synchronization
        """
        result=False
        if self.source.sitedir is not None:
            site_path=f"{self.source.sitedir}/{self.wiki_site.hostname}"
            print(f"site sync check {site_path}...")
            marker_file="LocalSettings.php"
            source_path=f"{self.source.hostname}:{site_path}"
            proc=self.target.remote.rsync(
                source_path=source_path,
                target_path=site_path,
                marker_file=marker_file,
                message=f"{self.wiki_site.hostname}",
                update=self.force or self.update,
                do_mkdir=True,
                do_permissions=True
            )
            if proc.returncode==0:
                print("✅ sync done")
                result=True
            if self.use_git:
                proc=self.git_target(target_path=site_path)
                if proc.returncode==0:
                    print("✅ git committed")
                else:
                    result=False
        return result

    def check_sql_backup(self)->bool:
        """
        Ensure a fresh SQL backup exists on the source.
        If not, create it. Then check the target and copy the backup if needed.
        """
        result=False
        print("SQL Backup check ...")
        wiki = self.wiki_site
        wiki.configure_of_settings()

        source_base_path = f"{self.source.sql_backup_path}/today/"
        target_base_path = f"{self.target.sql_backup_path}/today/"
        source_backup_path = f"{source_base_path}{wiki.database_setting}_full.sql"
        target_backup_path = f"{target_base_path}{wiki.database_setting}_full.sql"

        source_age = Checks.check_age(self.source.remote, source_backup_path)
        target_age = Checks.check_age(self.target.remote, target_backup_path)
        source_display = f"{source_age:.1f}" if source_age is not None else "❌"
        target_display = f"{target_age:.1f}" if target_age is not None else "❌"
        age_hint = f"{source_display}d → {target_display}d"
        print(f"found backups with age {age_hint}")
        if source_age is None or source_age > 1.0:
            print(f"❌ no {source_backup_path} — creating now")
            sql_backup = SqlBackup(
                backup_host=self.source.remote.host,
                backup_path=self.source.sql_backup_path,
                debug=self.debug,
                progress=self.progress,
            )
            sql_backup.perform_backup(database=wiki.database_setting, full=True)
            source_age = Checks.check_age(self.source.remote, source_backup_path)
            if source_age is None or source_age > 1.0:
                print("❌ Backup creation failed or still outdated.")
                return False

        if target_age:
            age_diff_secs=(target_age-source_age)*86400
        # more than 1 minute difference
        if target_age is None or age_diff_secs>60:
            source_path = f"{self.source.remote.host}:{source_backup_path}"
            target_path = f"{target_backup_path}"
            print(f"⚠️ Copying backup from source to target: {source_path} → {target_path}")
            # pull from target
            self.target.remote.run_cmds(
                {
                    "create directory": f"sudo mkdir -p {target_base_path}",
                    "chown": f"sudo chown {self.target.remote.uid} {target_base_path}",
                    "chgrp": f"sudo chgrp {self.target.remote.gid} {target_base_path}"
                }
            )
            proc=self.target.remote.remote_copy(source_path, target_path)
            result=proc.returncode==0
            if not result:
                msg=f"❌ Backup copy {source_path}→{target_path} failed:{proc.stderr}"
            else:
                msg=f"✅ Backup copy {target_path} created"
            print(msg)
        else:
            print(f"✅ Target backup is up to date.")
            result=True
        return result

class TransferSite:
    """
    transfer a MediaWiki Site
    """

    def __init__(self, args):
        """
        constructor
        """
        self.args = args
        self.source = args.source
        self.target = args.target
        self.sitename = args.sitename
        self.servers = Servers.of_config_path()
        self.log = Log()
        self.log.do_print = args.verbose

    def check_apache(self):
        """
        check the apache configurations
        """
        for server in self.get_selected_servers():
            server.probe_apache_configs()
            for site in server.wikis.values():
                if site.apache_config:
                    print(f"{server.hostname}:{site.apache_config}")
        pass

    def check_sql_backup(self):
        """
        check the backup state of the selected servers sites
        """
        for server in self.get_selected_servers():
            files = server.remote.listdir(server.sql_backup_path + "/today", "*.sql")
            if files:
                for filepath in files:
                    Checks.check_age(server.remote,filepath,1.0)

    def check_database(self):
        """
        check the database access
        """
        index=0
        for wiki in self.get_selected_wikis():
            if wiki.localSettings is None:
                wiki.configure_of_settings()
                index+=1
                print(f"{index:2d}:{wiki.database} vs {wiki.database_setting} dbUser:{wiki.dbUser}")
                pass

    def check_endpoints(self):
        """
        check that we have endpoint configurations
        """
        for server in self.get_selected_servers():
            server.init_endpoints(self.servers.get_config_path())
            if self.args.debug:
                server.remote.log.dump()

    def check_site(self):
        """
        Prints reachability status of sites
        Returns True if both are reachable, else False.
        """
        index = 0
        for wiki in self.get_selected_wikis():
            index += 1
            self.check_remote(wiki.remote, index)

    def get_wiki_user(self, wikisite: WikiSite, purpose: str):
        """
        get the wikiuser and set the remote
        """
        wikiuser = wikisite.init_wikiuser_and_backup()
        if wikiuser is None:
            self.log.log("❌", purpose, f"invalid wikiuser {wikisite.wikiId}")
        return wikiuser

    def check_recent_backups(self):
        """
        Check and display how many days ago the last backup was done for the selected wiki
        Returns the number of days since last backup
        """
        for wikisite in self.get_selected_wikis():
            wiki_user = self.get_wiki_user(wikisite, "recent backups")

            if wiki_user is None:
                continue
            wikisite.wiki_backup.show_age()

    def check_remote(self,remote:Remote,index:int=None)->bool:
        """
        check the availability of the given remote
        """
        avail_timestamp=remote.avail_check()
        ok = Site.state_symbol(avail_timestamp is not None)
        index_str = f"{index:02d}:" if index else ""
        print(f"{index_str}{remote.host:<26} {ok} {remote.symbol}  {avail_timestamp or ''}")
        if self.args.debug:
            remote.log.dump()
        return ok

    def check_family(self):
        """
        check the family probing
        """
        for server in self.get_selected_servers():
            wikis = self.servers.probe_wiki_family(server)

    def check_lamp(self):
        """
        Check LAMP stack availability (Linux, Apache, MySQL, PHP) on selected remotes.
        """
        index = 0
        for remote in self.get_selected_remotes():
            cmds = {
                "linux": "lsb_release -d",
                "apache": "apachectl -v",
                "mysql": "mysql --version",
                "php": "php -v"
            }
            remote.log.do_log=self.args.debug
            procs = remote.run_cmds(cmds,stop_on_error=False)
            results = {}
            for key, proc in procs.items():
                if proc.returncode == 0:
                    marker = "✅"
                    if key == "php":
                        version = proc.stdout.splitlines()[0] if proc.stdout else ""
                    elif key == "apache":
                        version = proc.stdout.splitlines()[0] if proc.stdout else ""
                    elif key == "mysql":
                        version = proc.stdout.strip()
                    elif key == "linux":
                        version = proc.stdout.strip()
                else:
                    marker = "❌"
                    version = ""
                results[key] = (marker, version)

            index += 1
            print(f"{index:2}: {remote}")
            for label in ["linux", "apache", "mysql", "php"]:
                marker, version = results[label]
                print(f"    {label:6}: {version} {marker}")

    def check_tools(self):
        """
        Check availability and versions of required tools on selected servers

        Tools are loaded from tools.yaml configuration
        """
        for server in self.get_selected_servers():
            print(f"\nServer: {server.hostname}")
            self.check_server_tools(server)

    def check_server_tools(self, server):
        """
        Check tools on a specific server
        """
        server.remote.log.do_log=self.args.debug
        for tool_name, tool in self.servers.tools.tools.items():
            cmd = f"source .profile;{tool.version_cmd}"
            output = server.remote.get_output(cmd)
            status_symbol = "✅" if output else "❌"
            version_info = output.split("\n")[0].strip() if output else "?"
            hint = version_info if status_symbol == "✅" else tool.install_cmd
            print(f" {tool_name:<12} {status_symbol} {hint}")

    def create_TransferTask(self) -> TransferTask:
        """
        create a transfer Task
        """
        wiki = self.servers.wikis_by_hostname.get(self.sitename)
        if wiki is None:
            self.log.log("❌", "transfer", f"invalid wiki {self.sitename}")
            return
        self.check_remote(wiki.remote)
        source_ok = self.source and self.source in self.servers.servers
        if not source_ok:
            self.log.log("❌", "transfer", f"invalid source {self.source}")
            return
        source_server = self.servers.servers.get(self.source)
        if not self.check_remote(source_server.remote):
            return
        target_ok = self.target and self.target in self.servers.servers
        if not target_ok:
            self.log.log("❌", "transfer", f"invalid target {self.target}")
            return
        target_server = self.servers.servers.get(self.target)
        if not self.check_remote(target_server.remote):
            return
        transferTask = TransferTask(wiki, source_server, target_server,force=self.args.force,update=self.args.update,use_git=self.args.git)
        transferTask.log=self.log
        return transferTask

    def transfer(self):
        """
        transfer the given site from the source to the target server
        """
        transferTask = self.create_TransferTask()
        transferTask.login()
        self.log.log("✅", "transfer", transferTask.site.version)
        if not transferTask.check_ssh():
            return
        if not transferTask.check_sql_backup():
            return
        if not  transferTask.check_site_sync():
            return


    def as_iterator(self, items: Iterable[T], desc: str) -> Iterator[T]:
        """
        Return an iterator over the items, using tqdm if progress is requested.

        Args:
            items (Iterable): the collection to iterate
            desc (str): progress bar description

        Returns:
            Iterator: tqdm or plain iterator
        """
        return tqdm(items, desc=desc) if self.args.progress else iter(items)

    def get_selected_remotes_list(self)->List[Remote]:
        """
        get the selected remote server access API including
        container and native options
        """
        remotes=[]
        servers=self.get_selected_servers()
        for server in servers:
            remotes.append(server.remote)
        for wiki in self.get_selected_wikis_list():
            if wiki.container is not None:
                remotes.append(wiki.remote)
        return remotes

    def get_selected_remotes(self) -> Iterator[Remote]:
        """
        Return an iterator over selected remote server access APIs, including container and native options.

        Returns:
            Iterator[Remote]: selected remotes, optionally shown with a progress bar
        """
        remotes = self.get_selected_remotes_list()
        remote_iterator = self.as_iterator(remotes, "remotes")
        return remote_iterator


    def get_selected_servers_list(self):
        """
        get all selected servers
        """
        if self.args.all:
            servers = list(self.servers.servers.values())
        else:
            servers = []
            if self.source and self.source in self.servers.servers:
                servers.append(self.servers.servers.get(self.source))
            if self.target and self.target in self.servers.servers:
                servers.append(self.servers.servers.get(self.target))
        return servers

    def get_selected_servers(self) -> Iterator[Server]:
        """
        Return an iterator over selected servers based on arguments.

        Returns:
            Iterator[Server]: selected servers, optionally shown with a progress bar
            """
        servers = self.get_selected_servers_list()
        server_iterator = self.as_iterator(servers, "Processing servers")
        return server_iterator

    def get_selected_wikis_list(self)->List[WikiSite]:
        wikis=[]
        if self.args.all:
            for server in self.servers.servers.values():
                for wiki in server.wikis.values():
                    wikis.append(wiki)
        else:
            if self.sitename:
                wiki = self.servers.wikis_by_hostname.get(self.sitename)
                if wiki:
                    wikis.append(wiki)
        return wikis

    def get_selected_wikis(self) -> Iterator[WikiSite]:
        """
        Return an iterator over selected wikis based on arguments.

        Returns:
            Iterator[WikiSite]: selected wikis, optionally shown with a progress bar
        """
        wikis = self.get_selected_wikis_list()
        wiki_iter = self.as_iterator(wikis, "wikis")
        return wiki_iter


    def list_sites(self) -> None:
        """
        List all available sites from all servers
        """
        print("Available sites:")
        for server_name, server in self.servers.servers.items():
            print(f"Server: {server_name}")
            for wiki_name, wiki in server.wikis.items():
                database_info = f" (DB: {wiki.database})" if wiki.database else ""
                print(f"  - {wiki_name}{database_info}")

    def wiki_backup(self):
        """
        perform the backup
        """
        for wikisite in self.get_selected_wikis():
            wikiuser = self.get_wiki_user(wikisite, "backup")
            if wikiuser is None:
                continue
            wikisite.wiki_backup.backup(
                days=self.args.days, show_progress=self.args.progress
            )


class TransferSiteCmd(BaseCmd):
    """
    tools to transfer a MediaWiki site from one server to another
    """

    def add_arguments(self, parser: ArgumentParser):
        """
        add arguments to the parse
        """
        super().add_arguments(parser)
        parser.add_argument(
            "-ca",
            "--check-apache",
            action="store_true",
            help="check Apache configuration for selected sites",
        )
        parser.add_argument(
            "-cd",
            "--check-database",
            action="store_true",
            help="check database access for selected sites",
        )
        parser.add_argument(
            "-cs",
            "--check-site",
            action="store_true",
            help="check site state of selected sites",
        )
        parser.add_argument(
            "-cl",
            "--check-lamp",
            action="store_true",
            help="check LAMP state of selected servers/sites",
        )
        parser.add_argument(
            "-ct",
            "--check-tools",
            action="store_true",
            help="check availability of needed tools on selected sites",
        )
        parser.add_argument(
            "-cb",
            "--check-backup",
            action="store_true",
            help="check backup state of selected wikis",
        )
        parser.add_argument(
            "-ce",
            "--check-endpoints",
            action="store_true",
            help="check endpoints for sites",
        )
        parser.add_argument(
            "-cf",
            "--check-family",
            action="store_true",
            help="check family state of selected sites",
        )
        parser.add_argument(
            "--backup",
            action="store_true",
            help="create a backup wiki",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="update pages and images",
        )
        parser.add_argument(
            "--progress", action="store_true", help="show progress bars"
        )
        parser.add_argument(
            "-g", "--git", action="store_true", help="use git for site directory"
        )

        parser.add_argument(
            "--transfer",
            action="store_true",
            help="transfer the given site",
        )
        parser.add_argument(
            "-ls",
            "--list-sites",
            action="store_true",
            help="list available sites",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="perform action on all sites",
        )
        parser.add_argument(
            "-sn", "--sitename", help="specify the site name (also used to derive apache config name)"
        )
        parser.add_argument(
            "-al", "--alias", help="specify the alias website hostname to use e.g. for backup sites"

        )
        parser.add_argument(
            "-cn", "--container", help="specify the container name"
        )

        parser.add_argument("-s", "--source", help="specify the source server")
        parser.add_argument("-t", "--target", help="specify the target server")
        parser.add_argument(
            "-mrb",
            "--recent-backup",
            action="store_true",
            help="show most recent backup",
        )
        parser.add_argument(
            "-wb", "--wikibackup", action="store_true", help="run wikibackup task"
        )
        parser.add_argument(
            "--days", type=int, default=2, help="days of changes to include"
        )

    def handle_args(self, args):
        handled = super().handle_args(args)
        tsite = TransferSite(args)
        if args.check_apache:
            tsite.check_apache()
            handled = True
        if args.check_backup:
            tsite.check_backup()
            handled = True
        if args.check_database:
            tsite.check_database()
            handlet = True
        if args.check_endpoints:
            tsite.check_endpoints()
            handled = True
        if args.check_family:
            tsite.check_family()
            handled = True
        if args.check_lamp:
            tsite.check_lamp()
            handled = True
        if args.check_site:
            tsite.check_site()
            handled = True
        if args.check_tools:
            tsite.check_tools()
            handled = True
        if args.list_sites:
            tsite.list_sites()
            handled = True

        if args.transfer:
            if not args.sitename or not args.source or not args.target:
                print("need sitename, source and target for transfer!")
                self.parser.print_help()
            else:
                handled = tsite.transfer()
        if args.recent_backup:
            if not args.sitename and not args.all:
                print("Need sitename or --all for recent backup check!")
                self.parser.print_help()
            else:
                tsite.check_recent_backups()
                handled = True
        if args.wikibackup:
            if not args.sitename:
                print("need sitename for wikibackup!")
                self.parser.print_help()
            else:
                tsite.wiki_backup()
                handled = True
        return handled


def main():
    """
    command line access
    """
    version = Version()
    version.description = "Transfer mediawiki site from one server to another"
    exit_code = TransferSiteCmd.main(version)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
