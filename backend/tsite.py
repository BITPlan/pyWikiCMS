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

from basemkit.base_cmd import BaseCmd
from basemkit.persistent_log import Log
from basemkit.shell import Shell
from profiwiki.version import Version
from backend.server import Servers



class TransferSite:
    """
    transfer a MediaWiki Site
    """

    def __init__(self, args):
        """
        constructor
        """
        self.source = args.source
        self.target = args.target
        self.sitename = args.sitename
        self.shell = Shell()
        self.log = Log()
        self.servers = Servers.of_config_path()

    def is_reachable(self, server: str, timeout: int = 5) -> bool:
        """
        Returns True if SSH to server is possible, otherwise False.
        """
        cmd = f"ssh -o ConnectTimeout={timeout} {server} echo ok"
        result = self.shell.run(cmd, tee=False)
        if result.returncode != 0:
            self.log.log("❌", "ssh-check", server)
            return False
        if "ok" not in result.stdout:
            self.log.log("⚠️", "ssh-check", server)
        self.log.log("✅", "ssh-check", server)


    def checksite(self) -> bool:
        """
        Prints reachability status of source and target.
        Returns True if both are reachable, else False.
        """
        self.is_reachable(self.source)
        self.is_reachable(self.target)
        self.dump_log()

    def checkapache(self):
        """
        check the apache configurations for source and target
        """

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
