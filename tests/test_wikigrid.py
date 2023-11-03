"""
Created on 2023-10-31

@author: wf
"""
from ngwidgets.webserver_test import WebserverTest
from frontend.wikigrid import WikiGrid
from frontend.webserver import CmsWebServer
from frontend.cmsmain import CmsMain

class TestWikiGrid(WebserverTest):
    """
    test the wikiGrid functionality
    """
    
    def setUp(self,debug=False, profile=True):
        server_class=CmsWebServer
        cmd_class=CmsMain
        WebserverTest.setUp(self, server_class, cmd_class, debug=debug, profile=profile)       
         
    def testWikiGrid(self):
        """
        test wiki grid 
        """
        wiki_grid=WikiGrid(self.ws.app)
        debug=True
        if debug:
            print(f"found {len(wiki_grid.lod)} wikis")
        pass
