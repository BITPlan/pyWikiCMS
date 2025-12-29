"""
Created on 2022-11-24

@author: wf
"""

import sys
from argparse import ArgumentParser

from ngwidgets.cmd import WebserverCmd

from frontend.webserver import CmsWebServer


class CmsMain(WebserverCmd):
    """
    ContentManagement System Main Program
    """

    def getArgParser(self, description: str, version_msg) -> ArgumentParser:
        """
        override the default argparser call
        """
        parser = super().getArgParser(description, version_msg)
        parser.add_argument(
            "--sites", nargs="+", required=False,
        help="space-separated list of sites (or use comma-separated string)"        )
        return parser


def main(argv: list = None):
    """
    main call
    """
    cmd = CmsMain(config=CmsWebServer.get_config(), webserver_cls=CmsWebServer)
    exit_code = cmd.cmd_main(argv)
    return exit_code


DEBUG = 0
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    sys.exit(main())
