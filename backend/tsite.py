"""
Created on 2025-06-15
based on original tsite bash script
Tools to transfer a mediawiki site from one server to another
to e.g. migrate the LAMP stack elements or move from a farm based
to a dockerized environment

@author: wf
"""

from argparse import ArgumentParser
import sys

from backend.server import Servers
from backend.site import Site
from basemkit.base_cmd import BaseCmd
from profiwiki.version import Version


class TransferSite:
    """
    transfer a MediaWiki Site
    """

    def __init__(self, args):
        """
        constructor
        """
        self.args=args
        self.source = args.source
        self.target = args.target
        self.sitename = args.sitename
        self.servers = Servers.of_config_path()

    def checksite(self):
        """
        Prints reachability status of sites
        Returns True if both are reachable, else False.
        """
        index=0
        for wiki in self.get_selected_wikis():
            ssh_timestamp=wiki.remote.ssh_able()
            ok=Site.state_symbol(ssh_timestamp is not None)
            index+=1
            print(f"{index:02d}: {wiki.hostname:<26} {ok} {ssh_timestamp or ''}")
            if self.args.debug:
                wiki.remote.log.dump()

    def checkfamily(self):
        """
        check the family probing
        """
        for server in self.get_selected_servers():
            wikis=server.probe_wiki_family()

    def checkapache(self):
        """
        check the apache configurations
        """
        pass

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
                wiki=self.servers.wikis_by_name.get(self.sitename)
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
            "-cs",
            "--checksite",
            action="store_true",
            help="check site state of source/target",
        )
        parser.add_argument(
            "-cf",
            "--checkfamily",
            action="store_true",
            help="check family state of source/target",
        )
        parser.add_argument(
            "-ca",
            "--checkapache",
            action="store_true",
            help="check Apache configuration for the site",
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
        handled=super().handle_args(args)
        tsite = TransferSite(args)
        if args.checksite:
            tsite.checksite()
            handled=True
        if args.checkfamily:
            tsite.checkfamily()
            handled=True
        if args.list_sites:
            tsite.list_sites()
            handled = True
        if args.checkapache:
            handled=tsite.checkapache()
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
