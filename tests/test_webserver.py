"""
Created on 2020-07-11

@author: wf
"""

import warnings

from ngwidgets.webserver_test import WebserverTest

from backend.server import Server
from backend.site import FrontendSite
from frontend.cmsmain import CmsMain
from frontend.webserver import CmsWebServer
from tests.test_wikicms import TestWikiCMS


class TestWebServer(WebserverTest):
    """
    test the pyWikiCms Server
    """

    def setUp(self, debug=False, profile=True):
        server_class = CmsWebServer
        cmd_class = CmsMain
        WebserverTest.setUp(self, server_class, cmd_class, debug=debug, profile=profile)
        self.server = TestWebServer.getServer()
        # make sure tests run in travis
        sites = list(self.server.frontends.keys())
        self.ws.wiki_frontends.enableSites(sites)
        pass

    @staticmethod
    def getServer():
        """
        initialize the server
        """
        warnings.simplefilter("ignore", ResourceWarning)
        server = Server(name="test", hostname="localhost")
        server.logo = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Desmond_Llewelyn_01.jpg/330px-Desmond_Llewelyn_01.jpg"
        server.frontends = {
            "cr": FrontendSite(name="cr", wikiId="cr"),
            "sharks": FrontendSite(name="sharks", wikiId="wiki", defaultPage="Sharks"),
            "www": FrontendSite(name="www", wikiId="wiki", defaultPage="Welcome"),
        }
        for frontend in server.frontends.values():
            # make sure ini file is available
            TestWikiCMS.getSMW_WikiUser(frontend.wikiId)
        return server

    def testWebServer(self):
        """
        test the WebServer
        """
        queries = ["/www/Joker", "/", "/www/{Illegal}"]
        expected = ["Joker", "<title>pyWikiCMS</title>", "invalid char"]
        debug = self.debug
        # debug = True
        for i, query in enumerate(queries):
            html = self.get_html(query)
            if debug:
                print(f"{i+1}:{query}\n{html}")
            ehtml = expected[i]
            self.assertTrue(ehtml, ehtml in html)

    def testRevealIssue20(self):
        """
        test Issue 20
        https://github.com/BITPlan/pyWikiCMS/issues/20
        support reveal.js slideshow if frame is "reveal" #20
        """
        html = self.get_html("www/SMWConTalk2015-05")
        if self.debug:
            print(html)
        self.assertTrue("reveal.min.css" in html)
        self.assertTrue("Reveal.initialize({" in html)
