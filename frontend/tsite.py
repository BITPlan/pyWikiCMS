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

from basemkit.base_cmd import BaseCmd
from basemkit.shell import Shell
from basemkit.persistent_log import Log
from profiwiki.version import Version

class TransferSite:
    """
    transfer a MediaWiki Site
    """
    def __init__(self,args):
        """
        constructor
        """
        self.source = args.source
        self.target = args.target
        self.shell=Shell()
        self.log=Log()

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
        for entry in self.log.entries:
            print(entry.as_text())



class TransferSiteCmd(BaseCmd):
    """
    tools to transfer a MediaWiki site from one server to another
    """

    def add_arguments(self, parser:ArgumentParser):
        """
        add arguments to the parse
        """
        super().add_arguments(parser)
        parser.add_argument(
            "-cs", "--checksite",
            action="store_true",
            help="check site state of source/target"
        )
        parser.add_argument(
            "-s", "--source",
            help="specify the source server"
        )
        parser.add_argument(
            "-t", "--target",
            help="specify the target server"
        )


    def handle_args(self, args):
        if super().handle_args(args):
            return True
        tsite=TransferSite(args)
        if args.checksite:
            tsite.checksite()
            return True
        return False

def main():
    """
    command line access
    """
    version=Version()
    version.description="Transfer mediawiki site from one server to another"
    exit_code = TransferSiteCmd.main(version)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

