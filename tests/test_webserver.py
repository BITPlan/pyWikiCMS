'''
Created on 2020-07-11

@author: wf
'''
import unittest
from frontend.wikicms import Frontends
from frontend.app import AppWrap
from tests.test_wikicms import TestWikiCMS

class TestWebServer(unittest.TestCase):
    ''' see https://www.patricksoftwareblog.com/unit-testing-a-flask-application/ '''

    def setUp(self):
      
        TestWebServer.initFrontends()
        import frontend.webserver 
        app=frontend.webserver.app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        self.app = app.test_client()
        self.debug=False
        # make sure tests run in travis
        sites=['or','cr','sharks']
        frontend.webserver.appWrap.enableSites(sites)
        pass

    def tearDown(self):
        pass
    
    @staticmethod
    def initFrontends():
        '''
        initialize the frontends
        '''
        Frontends.homePath="/tmp"
        frontends=Frontends()
        frontends.frontendConfigs=[
            {
             'site':'or',
             'wikiId':'or', 
             'template':'bootstrap.html',
             'defaultPage':'Frontend'
            },
            {
             'site': 'cr',
             'wikiId':'cr', 
             'template':'bootstrap.html',
             'defaultPage':'Main Page'
            },
            {
             'site': 'sharks',
             'wikiId':'wiki', 
             'template':'bootstrap.html',
             'defaultPage':'Sharks'
            }
        ]
        for frontendConfigs in frontends.frontendConfigs:
            # make sure ini file is available
            wikiId=frontendConfigs["wikiId"]
            TestWikiCMS.getSMW_WikiUser(wikiId)
        frontends.store()
        frontends.load()
        return frontends
    
    def testSplit(self):
        '''
        test splitting the path into site an path
        '''
        paths=['admin/','or/test']
        expected=[('admin','/'),('or','/test')]
        for i,testpath in enumerate(paths):
            site,path=AppWrap.splitPath(testpath)
            if self.debug:
                print("%s:%s" % (site,path))
            esite,epath=expected[i]
            self.assertEqual(esite,site)
            self.assertEqual(epath,path)

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
        for i,query in enumerate(queries):
            response=self.app.get(query)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data is not None)
            html=response.data.decode()
            if self.debug:
                print(html)
            ehtml=expected[i]
            self.assertTrue(ehtml,ehtml in html)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
