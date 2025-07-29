"""
Created on 2025-06-15
based on original tsite bash script
Tools to transfer a mediawiki site from one server to another
to e.g. migrate the LAMP stack elements or move from a farm based
to a dockerized environment

@author: wf
"""

import sys
from argparse import ArgumentParser
from dataclasses import dataclass

from basemkit.base_cmd import BaseCmd
from basemkit.persistent_log import Log
from profiwiki.version import Version
from wikibot3rd.smw import SMWClient
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.wikiuser import WikiUser

from backend.server import Server, Servers
from backend.site import Site, WikiSite


@dataclass
class TransferTask:
    wiki_site: WikiSite
    source: Server
    target: Server
    debug: bool = False
    progress: bool = True
    query_division: int = 50

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

    def check_backup(self):
        """
        check the backup state of the selected servers sites
        """
        for server in self.get_selected_servers():
            files = server.remote.listdir(server.sql_backup_path + "/today", "*.sql")
            if files:
                for filepath in files:
                    stats = server.remote.get_file_stats(filepath)
                    if stats:
                        age_marker = "✅" if stats.age_days < 1.0 else "❌"
                        print(
                            f"{server.hostname}:{filepath} {stats.age_days:.2f} d {age_marker}"
                        )

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
            self.check_wikisite(wiki, index)

    def check_wikisite(self, site, index: int = None) -> bool:
        """
        check the given wiki
        """
        ssh_timestamp = site.remote.ssh_able()
        ok = Site.state_symbol(ssh_timestamp is not None)
        index_str = f"{index:02d}:" if index else ""
        print(f"{index_str}{site.hostname:<26} {ok} {ssh_timestamp or ''}")
        if self.args.debug:
            site.remote.log.dump()
        return ok

    def check_family(self):
        """
        check the family probing
        """
        for server in self.get_selected_servers():
            wikis = server.probe_wiki_family()

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
        self.check_site(wiki)
        source_ok = self.source and self.source in self.servers.servers
        if not source_ok:
            self.log.log("❌", "transfer", f"invalid source {self.source}")
            return
        source_server = self.servers.servers.get(self.source)
        if not self.check_site(source_server):
            return
        target_ok = self.target and self.target in self.servers.servers
        if not target_ok:
            self.log.log("❌", "transfer", f"invalid target {self.target}")
            return
        target_server = self.servers.servers.get(self.target)
        if not self.check_site(target_server):
            return
        transferTask = TransferTask(wiki, source_server, target_server)
        return transferTask

    def transfer(self):
        """
        transfer the given site from the source to the target server
        """
        transferTask = self.create_TransferTask()
        transferTask.login()
        self.log.log("✅", "transfer", transferTask.site.version)

    def get_selected_servers(self):
        """
        Generator that yields selected servers based on arguments
        """
        if self.args.all:
            # Yield all servers
            for server in self.servers.servers.values():
                yield server
        else:
            if self.source and self.source in self.servers.servers:
                yield self.servers.servers.get(self.source)
            if self.target and self.target in self.servers.servers:
                yield self.servers.servers.get(self.target)

    def get_selected_wikis(self):
        """
        Generator that yields selected wikis based on arguments

        Yields:
            tuple: (server_name, wiki_name, wiki) for each selected wiki
        """
        if self.args.all:
            # Yield all wikis from all servers
            for server in self.servers.servers.values():
                for wiki in server.wikis.values():
                    yield wiki
        else:
            if self.sitename:
                wiki = self.servers.wikis_by_hostname.get(self.sitename)
                yield wiki

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
            "-cs",
            "--check-site",
            action="store_true",
            help="check site state of selected sites",
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
            help="check backup state of selected wikis",
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
            "-sn", "--sitename", help="specify the site name (also used as conf name)"
        )

        parser.add_argument("-s", "--source", help="specify the source server")
        parser.add_argument("-t", "--target", help="specify the target server")

    def handle_args(self, args):
        handled = super().handle_args(args)
        tsite = TransferSite(args)
        if args.check_apache:
            tsite.check_apache()
            handled = True
        if args.check_backup:
            tsite.check_backup()
            handled = True
        if args.check_endpoints:
            tsite.check_endpoints()
            handled = True
        if args.check_family:
            tsite.check_family()
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
                print("need sitename, source and target!")
                self.parser.print_help()
            else:
                handled = tsite.transfer()
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
