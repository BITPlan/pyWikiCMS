'''
Created on 2022-11-24

@author: wf
'''
from ngwidgets.cmd import WebserverCmd
from frontend.webserver import CmsWebServer
from argparse import ArgumentParser
import sys

class CmsMain(WebserverCmd):
    """
    ContentManagement System Main Program
    """
        
    def getArgParser(self,description:str,version_msg)->ArgumentParser:
        """
        override the default argparser call
        """        
        parser=super().getArgParser(description, version_msg)
        parser.add_argument('--sites',nargs='+',required=False,help="the sites to enable")
        return parser
    
def main(argv:list=None):
    """
    main call
    """
    cmd=CmsMain(config=CmsWebServer.get_config(),webserver_cls=CmsWebServer)
    exit_code=cmd.cmd_main(argv)
    return exit_code
        
DEBUG = 0
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    sys.exit(main())