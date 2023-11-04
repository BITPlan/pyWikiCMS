'''
Created on 2020-07-11

@author: wf
'''
import warnings
from frontend.server import Server
from frontend.webserver import CmsWebServer
from tests.test_wikicms import TestWikiCMS
from ngwidgets.webserver_test import WebserverTest
from frontend.cmsmain import CmsMain

class TestWebServer(WebserverTest):
    """
    test the pyWikiCms Server
    """
    
    def setUp(self,debug=False, profile=True):
        server_class=CmsWebServer
        cmd_class=CmsMain
        WebserverTest.setUp(self, server_class, cmd_class, debug=debug, profile=profile)       
        self.server=TestWebServer.initServer()
        # make sure tests run in travis
        sites=['cr','sharks','www']        
        self.ws.enableSites(sites)
        pass
    
    @staticmethod
    def initServer():
        '''
        initialize the server
        '''
        warnings.simplefilter("ignore", ResourceWarning)
        Server.homePath="/tmp"
        server=Server()
        server.logo="https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Desmond_Llewelyn_01.jpg/330px-Desmond_Llewelyn_01.jpg"
        server.frontendConfigs=[
            {
             'site': 'cr',
             'wikiId':'cr', 
             'defaultPage':'Main Page'
            },
            {
             'site': 'sharks',
             'wikiId':'wiki', 
             'defaultPage':'Sharks'
            },
            {
             'site': 'www',
             'wikiId':'wiki', 
             'defaultPage':'Welcome',
            }
        ]
        for frontendConfigs in server.frontendConfigs:
            # make sure ini file is available
            wikiId=frontendConfigs["wikiId"]
            TestWikiCMS.getSMW_WikiUser(wikiId)
        server.store()
        server.load()
        return server
    
    def testConfig(self):
        '''
        check config
        '''
        path=self.server.getStorePath()
        if self.debug:
            print(path)
        self.assertTrue("/tmp" in path)
    
    def test_extract_site_and_path(self):
        """
        Test splitting the path into site and path.
        """
        # Test paths and their expected results.
        paths = ['admin/', 'or/test']
        expected_results = [('admin', '/'), ('or', '/test')]

        for index, test_path in enumerate(paths):
            # Extract site and path using the Webserver method.
            site, path = CmsWebServer.extract_site_and_path(test_path)

            # If debugging is enabled, print the results.
            if getattr(self, 'debug', False):
                print(f"Site: {site}, Path: {path}")

            # Get the expected site and path.
            expected_site, expected_path = expected_results[index]

            # Assert that the results match the expectations.
            self.assertEqual(expected_site, site)
            self.assertEqual(expected_path, path)
            
    def testWebServer(self):
        ''' 
        test the WebServer
        '''
        queries=['/','/or/test','/or/{Illegal}']
        expected=[
            "admin",
            "Frontend",
            "invalid char"
        ]
        #self.debug=True
        for i,query in enumerate(queries):
            html=self.getHtml(query)
            ehtml=expected[i]
            self.assertTrue(ehtml,ehtml in html)
            
    def testReveal(self):
        '''
        test Issue 20
        https://github.com/BITPlan/pyWikiCMS/issues/20
        support reveal.js slideshow if frame is "reveal" #20
        '''
        html=self.getHtml("www/SMWConTalk2015-05")
        if self.debug:
            print(html)
        self.assertTrue("reveal.min.css" in html)
        self.assertTrue("Reveal.initialize({" in html)
