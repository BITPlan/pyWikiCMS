"""
Created on 2025-06-15
based on original tsite bash script
Tools to transfer a mediawiki site from one server to another
to e.g. migrate the LAMP stack elements or move from a farm based
to a dockerized environment

@author: wf
"""

import base64
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, Iterator, List, TypeVar

from basemkit.base_cmd import BaseCmd
from basemkit.persistent_log import Log
from basemkit.profiler import Profiler
from tqdm import tqdm
from wikibot3rd.smw import SMWClient
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.wikiuser import WikiUser

from backend.remote import Remote, RunConfig
from backend.server import Server, Servers
from backend.site import Site, WikiSite
from backend.sql_backup import SqlBackup
from frontend.version import Version

# enable generic types
T = TypeVar("T")


class Checks:

    @classmethod
    def check_age(cls, remote: Remote, filepath: str, days: float = 1.0) -> float:
        stats = remote.get_file_stats(filepath)
        age = None
        if stats:
            age = stats.age_days
            ok = stats.age_days <= days
            age_marker = "✅" if ok else "❌"
            print(f"{remote.host}:{filepath} {stats.age_days:.2f} d {age_marker}")
        return age


@dataclass
class TransferTask:
    wiki_site: WikiSite
    source: Server
    target: Server
    args: Namespace
    debug: bool = False
    force: bool = False
    update: bool = (False,)
    progress: bool = True
    use_git: bool = False
    query_division: int = 50
    # Non-persistent calculated fields
    log: Log = field(default=None, init=False, repr=False)
    error: Exception = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self.force = self.args.force
        self.update = self.args.update
        self.use_git = self.args.git
        self.wikiUser = WikiUser.ofWikiId(self.wiki_site.wikiId, lenient=True)
        self.wikiClient = WikiClient.ofWikiUser(self.wikiUser)
        self.site = None
        self.smwClient = None
        try:
            self.site = self.wikiClient.get_site()
        except Exception as ex:
            self.error = ex
        if self.site:
            self.smwClient = SMWClient(
                self.site,
                showProgress=self.progress,
                queryDivision=self.query_division,
                debug=self.debug,
            )

    def login(self):
        """
        login to the source wiki
        """
        wu = self.wikiUser
        # bot login
        if "@" in wu.user:
            self.wikiClient.login()
        else:
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
        remote = self.target.remote
        remote.log.do_log = self.debug
        git_dir = f"{target_path}/.git"
        git_stats = remote.get_file_stats(git_dir)

        if git_stats is None or not git_stats.is_directory:
            self.log.log("⚠️", "git", "git not initialized yet")

            git_cmds = {
                "init": f"cd {target_path} && git init",
                "add": f"cd {target_path} && git add *",
            }
            proc = remote.run_cmds_as_single_cmd(git_cmds)
            if proc.returncode != 0:
                self.log.log("❌", "git", proc.stderr)
                return proc
        else:
            self.log.log("✅", "git", "git initialized")
        # https://stackoverflow.com/questions/71849415/i-cannot-add-the-parent-directory-to-safe-directory-in-git
        git_relax = f"git config --global --add safe.directory {target_path}"
        proc = remote.run(git_relax)
        if proc.returncode != 0:
            self.log.log("❌", "git", proc.stderr)

        timestamp = datetime.now().strftime("%Y-%m-%d-%H_%M_%S")
        commit_cmd = f"cd {target_path} && git add *&& git commit -a -m 'tsite commit at {timestamp}'"
        proc = remote.run(commit_cmd)
        # Git returns 1 when nothing to commit - this is not an error
        is_nothing_to_commit = (
            proc.returncode == 1 and "nothing to commit" in proc.stdout
        )
        success = proc.returncode == 0 or is_nothing_to_commit
        # fix return code for downstream
        if is_nothing_to_commit:
            proc.returncode = 0
        status = "✅" if success else "❌"
        message = (
            "nothing to commit"
            if is_nothing_to_commit
            else f"commit changes at {timestamp}"
        )
        if not success:
            message += f"\n{proc.stdout}\n{proc.stderr}"
        self.log.log(status, "git", message)

        return proc

    def check_ssh(self) -> bool:
        """
        check the target site is available via ssh
        """
        avail = self.target.remote.avail_check() is not None
        return avail

    def check_site_sync(self) -> bool:
        """
        check the site synchronization
        """
        result = False
        if self.source.sitedir is not None:
            site_path = f"{self.source.sitedir}/{self.wiki_site.hostname}"
            print(f"site sync check {site_path}...")
            marker_file = "LocalSettings.php"
            source_path = f"{self.source.hostname}:{site_path}"
            run_config = RunConfig(
                update=self.force or self.update,
                do_mkdir=True,
                do_permissions=True,
                uid=33,  # www-data
                gid=33,  # www-data
            )
            proc = self.target.remote.rsync(
                source_path=source_path,
                target_path=site_path,
                marker_file=marker_file,
                message=f"{self.wiki_site.hostname}",
                run_config=run_config,
            )
            if proc.returncode == 0:
                print("✅ sync done")
                result = True
            if self.use_git:
                proc = self.git_target(target_path=site_path)
                if proc.returncode == 0:
                    print("✅ git committed")
                else:
                    result = False
        return result

    def get_wiki_sql(self):
        wiki = self.wiki_site
        wiki.configure_of_settings()
        self.source_base_path = f"{self.source.sql_backup_path}/today/"
        self.target_base_path = f"{self.target.sql_backup_path}/today/"
        self.source_backup_path = (
            f"{self.source_base_path}{wiki.database_setting}_full.sql"
        )
        self.target_backup_path = (
            f"{self.target_base_path}{wiki.database_setting}_full.sql"
        )

        return wiki

    def run_sql_cmds(self, sql_cmds) -> Dict[str, str]:
        """
        Run the given SQL commands and return a dict of results.

        Args:
            sql_cmds: list of (name, sql_cmd, db_for_cmd) tuples

        Returns:
            dict mapping name -> stdout
        """
        mysqlr = self.target.mysql_root_script
        sql_results = {}
        for name, sql_cmd, db_for_cmd in sql_cmds:
            mysql_cmd = f"{mysqlr}" + (f" -D {db_for_cmd}" if db_for_cmd else "")
            b64 = base64.b64encode(sql_cmd.encode()).decode()
            remote_cmd = f"printf %s {b64!r} | base64 -d | {mysql_cmd}"
            proc = self.target.remote.run(remote_cmd)
            success = proc.returncode == 0
            if success:
                print(f"✅ {sql_cmd}:{proc.stdout}")
                sql_results[name] = proc.stdout
            else:
                print(f"❌ {sql_cmd}:{proc.stderr}")
                break
        return sql_results

    def check_sql_restore(self) -> bool:
        """
        Ensure the SQL restore is done if need be
        """
        result = False
        print("SQL_Restore check ...")
        _wiki = self.get_wiki_sql()
        mysqlr = self.target.mysql_root_script

        database = self.wiki_site.database
        dbUser = self.wiki_site.dbUser
        dbPassword = self.wiki_site.dbPassword
        sql_cmds = [
            ("ping", "SELECT 1 AS COL1", None),
            ("show_tables", "SHOW TABLES", database),
        ]
        sql_results = self.run_sql_cmds(sql_cmds)
        # ping means the database is accessible
        if "ping" in sql_results:
            result = True
            # if show_tables fails the database does not exist
            if "show_tables" not in sql_results:
                # (name, sql, database)
                sql_cmds = [
                    ("create_db", f"CREATE DATABASE IF NOT EXISTS `{database}`", None),
                    (
                        "grant",
                        f"GRANT ALL PRIVILEGES ON `{database}`.* TO '{dbUser}'@'%' IDENTIFIED BY '{dbPassword}';",
                        None,
                    ),
                    ("show_tables", "SHOW TABLES", database),
                    (
                        "rev_count",
                        "SELECT COUNT(*) AS rev_count FROM revision;",
                        database,
                    ),
                ]
                sql_results = self.run_sql_cmds(sql_cmds)
                # restore if update flag is set or no rev_count
                do_restore = (
                    result and self.args.update or "rev_count" not in sql_results
                )
                if do_restore:
                    restore_cmd = (
                        f"pv {self.target_backup_path} | {mysqlr} -D {database}"
                    )
                    proc = self.target.remote.run(restore_cmd)
                    success = proc.returncode == 0
                    result = result and success
                    if success:
                        print(f"✅ restore:{proc.stdout}")
                    else:
                        print(f"❌ restore:{proc.stderr}")
        if result:
            sql_cmds = [
                ("user_count", "SELECT COUNT(*) AS user_count FROM user;", database),
                ("rev_count", "SELECT COUNT(*) AS rev_count FROM revision;", database),
            ]
            sql_results = self.run_sql_cmds(sql_cmds)
            result = len(sql_results) == 2
        return result

    def check_sql_backup(self) -> bool:
        """
        Ensure a fresh SQL backup exists on the source.
        If not, create it. Then check the target and copy the backup if needed.
        """
        result = False
        print("SQL Backup check ...")
        wiki = self.get_wiki_sql()

        source_age = Checks.check_age(self.source.remote, self.source_backup_path)
        target_age = Checks.check_age(self.target.remote, self.target_backup_path)
        source_display = f"{source_age:.1f}" if source_age is not None else "❌"
        target_display = f"{target_age:.1f}" if target_age is not None else "❌"
        age_hint = f"{source_display}d → {target_display}d"
        print(f"found backups with age {age_hint}")
        if source_age is None or source_age > 1.0:
            print(f"❌ no {self.source_backup_path} — creating now")
            sql_backup = SqlBackup(
                backup_host=self.source.remote.host,
                backup_path=self.source.sql_backup_path,
                debug=self.debug,
                progress=self.progress,
            )
            sql_backup.perform_backup(database=wiki.database_setting, full=True)
            source_age = Checks.check_age(self.source.remote, self.source_backup_path)
            if source_age is None or source_age > 1.0:
                print("❌ Backup creation failed or still outdated.")
                return False

        if target_age:
            age_diff_secs = (target_age - source_age) * 86400
        # more than 1 minute difference
        if target_age is None or age_diff_secs > 60:
            source_path = f"{self.source.remote.host}:{self.source_backup_path}"
            target_path = f"{self.target_backup_path}"
            print(
                f"⚠️ Copying backup from source to target: {source_path} → {target_path}"
            )
            # pull from target
            self.target.remote.run_cmds(
                {
                    "create directory": f"sudo mkdir -p {self.target_base_path}",
                    "chown": f"sudo chown {self.target.remote.uid} {self.target_base_path}",
                    "chgrp": f"sudo chgrp {self.target.remote.gid} {self.target_base_path}",
                }
            )
            run_config = RunConfig(force_local=True, ignore_container=True)
            scp_cmd = f"scp -p {source_path} {target_path}"
            proc = self.target.remote.run(scp_cmd, run_config=run_config)
            result = proc.returncode == 0
            if not result:
                msg = f"❌ Backup copy {source_path}→{target_path} failed:{proc.stderr}"
            else:
                msg = f"✅ Backup copy {target_path} created"
            print(msg)
        else:
            print(f"✅ Target backup is up to date.")
            result = True
        return result

    def get_apache_config(
        self, server_name: str, hostname: str, port: int = 9880
    ) -> str:
        """
        get the apache configuration for the given server_name and hostname
        """
        created_iso = datetime.now().isoformat()
        wiki_site = hostname
        site_name = wiki_site.split(".")[0]
        config_str = f"""#
# Apache site {server_name}
# Virtualhost {server_name}
# created {created_iso} by tsite script {Version.version}
# HTTP → HTTPS redirect
<VirtualHost *:80>
    ServerName {server_name}
    Redirect permanent / https://{server_name}/
    ErrorLog ${{APACHE_LOG_DIR}}/{hostname}_error.log
    CustomLog ${{APACHE_LOG_DIR}}/{hostname}_access.log combined
</VirtualHost>
# HTTPS reverse proxy
<VirtualHost *:443>
    ServerName {server_name}
    include ssl.conf

    ProxyPreserveHost On
    ProxyRequests Off

    # serve images locally and bypass proxy
    Alias /images/{site_name}/ "/var/www/mediawiki/sites/{wiki_site}/images/"
    Alias /images/ "/var/www/mediawiki/sites/{wiki_site}/images/"
    <Directory "/var/www/mediawiki/sites/{wiki_site}/images/">
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>
    ProxyPass /images/{site_name}/ !
    ProxyPass /images/ !

    ProxyPass / http://localhost:{port}/
    ProxyPassReverse / http://localhost:{port}/

    # add WikiSite info for family
    RequestHeader set X-Wiki-Site "{wiki_site}"

    ErrorLog ${{APACHE_LOG_DIR}}/{hostname}_error.log
    CustomLog ${{APACHE_LOG_DIR}}/{hostname}_access.log combined
</VirtualHost>"""
        return config_str

    def check_apache(self) -> bool:
        """
        check apache configuration or create new one
        """
        result = False
        server_name = f"{self.wiki_site.hostname}"
        if self.args.backup:
            server_name = f"{self.wiki_site.name}-{self.target.hostname}"
        self.target.probe_apache_configs()
        # first check the configuration
        config_path = self.target.apache_configs.get(server_name)
        if config_path is None or self.args.force:
            config_path = f"/etc/apache2/sites-available/{self.wiki_site.name}.conf"
            apache_config = self.get_apache_config(server_name, self.wiki_site.hostname)
            run_config = RunConfig()
            run_config.sudo_viatemp = True
            run_config.force_local = True
            run_config.ignore_container = True
            run_config.uid = 33  # www-data
            run_config.gid = 33  # www-data
            proc = self.target.remote.copy_string_to_file(
                apache_config, config_path, run_config=run_config
            )
            if proc.returncode == 0:
                msg = f"✅ apache config {config_path} for {server_name} created"
                result = True
            else:
                msg = f"❌ apache config {config_path} for {server_name}: {proc.stderr}"
        else:
            msg = f"✅ apache config {config_path} for {server_name} exists"
            result = True
        print(msg)
        # then check whether server is available
        vhost_site = Site(server_name)
        proc = vhost_site.ping()
        if proc.returncode == 0:
            msg = f"✅ ping {server_name} {proc.stdout}"
        else:
            cmd = f"sudo a2ensite {self.wiki_site.name}"
            proc = self.target.remote.run(cmd)
            if proc.returncode == 0:
                msg = f"✅ {proc.stdout}"
            else:
                msg = f"❌ {proc.stderr}"
            pass
        print(msg)
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
                    Checks.check_age(server.remote, filepath, 1.0)

    def check_database(self):
        """
        check the database access
        """
        index = 0
        for wiki in self.get_selected_wikis():
            if wiki.localSettings is None:
                wiki.configure_of_settings()
                index += 1
                print(
                    f"{index:2d}:{wiki.database} vs {wiki.database_setting} dbUser:{wiki.dbUser}"
                )
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

    def check_remote(self, remote: Remote, index: int = None) -> bool:
        """
        check the availability of the given remote
        """
        avail_timestamp = remote.avail_check()
        ok = Site.state_symbol(avail_timestamp is not None)
        index_str = f"{index:02d}:" if index else ""
        print(
            f"{index_str}{remote.host:<26} {ok} {remote.symbol}  {avail_timestamp or ''}"
        )
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
                "php": "php -v",
            }
            remote.log.do_log = self.args.debug
            procs = remote.run_cmds(cmds, stop_on_error=False)
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
        server.remote.log.do_log = self.args.debug
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
            available_count = len(self.servers.wikis_by_hostname)
            hint = f"invalid wiki '{self.sitename}' - use --list-sites to see {available_count} available sites or add {self.source}.yaml to {Servers.get_config_path()}"
            self.log.log("❌", "transfer", hint)
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
        transferTask = TransferTask(wiki, source_server, target_server, args=self.args)
        transferTask.log = self.log
        return transferTask

    def transfer(self):
        """
        transfer the given site from the source to the target server
        """
        total_prof = Profiler("transfer", profile=self.args.profile)
        transferTask = self.create_TransferTask()
        if not transferTask:
            self.log.log("❌", "transfer", "aborted before login")
            return
        if transferTask.error:
            self.log.log("❌", "transfer", str(transferTask.error))
        else:
            transferTask.login()
            self.log.log("✅", "transfer", transferTask.site.version)
        if not transferTask.check_ssh():
            return
        if self.args.transfer_all or self.args.transfer_sql:
            sql_prof = Profiler("sql backup", profile=self.args.profile)
            if not transferTask.check_sql_backup():
                return
            sql_prof.time()
        if self.args.transfer_all or self.args.transfer_sql:
            sql_prof = Profiler("sql restore", profile=self.args.profile)
            if not transferTask.check_sql_restore():
                return
            sql_prof.time()

        if self.args.transfer_all or self.args.transfer_site:
            sync_prof = Profiler("site sync", profile=self.args.profile)
            if not transferTask.check_site_sync():
                return
            sync_prof.time()
        if self.args.transfer_all or self.args.transfer_apache:
            apache_prof = Profiler("apache config", profile=self.args.profile)
            if not transferTask.check_apache():
                return
            apache_prof.time()
        total_prof.time(" total")

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

    def get_selected_remotes_list(self) -> List[Remote]:
        """
        get the selected remote server access API including
        container and native options
        """
        remotes = []
        servers = self.get_selected_servers()
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

    def get_selected_wikis_list(self) -> List[WikiSite]:
        wikis = []
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
            "--profile", action="store_true", help="profile timing of steps"
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
            "-tall",
            "--transfer-all",
            action="store_true",
            help="perform all transfer steps for for selected sites",
        )
        parser.add_argument(
            "-tapa",
            "--transfer-apache",
            action="store_true",
            help="transfer/create Apache configuration for selected sites",
        )
        parser.add_argument(
            "-tsql",
            "--transfer-sql",
            action="store_true",
            help="transfer sql",
        )
        parser.add_argument(
            "-tsit",
            "--transfer-site",
            action="store_true",
            help="rsync site directory including images",
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
            "-sn",
            "--sitename",
            help="specify the site name (also used to derive apache config name)",
        )
        parser.add_argument(
            "-al",
            "--alias",
            help="specify the alias website hostname to use e.g. for backup sites",
        )
        parser.add_argument("-cn", "--container", help="specify the container name")

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
