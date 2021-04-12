'''
Created on 2020-07-11

@author: wf
'''
import unittest
import warnings
import getpass
import os
from fb4.app import AppWrap
from frontend.server import Server
from tests.test_wikicms import TestWikiCMS
import tempfile

class TestWebServer(unittest.TestCase):
    ''' see https://www.patricksoftwareblog.com/unit-testing-a-flask-application/ '''

    def setUp(self):
        '''
        prepare everything needed for the tests
        '''
        self.debug=False
        self.server=TestWebServer.initServer()
        import frontend.webserver 
        app=frontend.webserver.app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        self.app=app
        self.client = app.test_client()
       
        # make sure tests run in travis
        sites=['or','cr','sharks','www']
        frontend.webserver.wcw.enableSites(sites)
        self.wcw=frontend.webserver.wcw
        pass

    def tearDown(self):
        pass
    
    def inPublicCI(self):
        '''
        are we running in a public Continuous Integration Environment?
        '''
        return getpass.getuser() in [ "travis", "runner" ];
    
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
            },
            {
             'site': 'www',
             'wikiId':'wiki', 
             'template':'design.html',
             'defaultPage':'Welcome',
             'packageFolder': '%s/www.wikicms' % tempfile.gettempdir(),
             'packageName': 'bitplan_webfrontend',
             'templateFolder': 'templates'
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
            
    def getHtml(self,path):
        response=self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data is not None)
        html=response.data.decode()
        if self.debug:
            print(html)
        return html

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
    
    def createPackage(self,packageFolder,templateFolder,moduleName,moduleCode,templateCode):
        moduleFolder="%s/%s" % (packageFolder,moduleName)
        os.makedirs(moduleFolder,exist_ok=True)
        absTemplateFolder="%s/%s" % (moduleFolder,templateFolder)
        os.makedirs(absTemplateFolder,exist_ok=True)
        modulePath="%s/__init__.py" % moduleFolder 
        with open(modulePath,"w") as moduleFile:
            moduleFile.write(moduleCode)
        templatePath="%s/test.html" % (absTemplateFolder)
        with open(templatePath,"w") as templateFile:
            templateFile.write(templateCode)
        
    def testIssue14Templates(self):
        '''
        test template handling
        '''
        # work around CI environment problem
        # https://github.com/pallets/jinja/issues/1365
        if self.inPublicCI():
            return
        packageFolder='%s/www.wikicms' % tempfile.gettempdir()
        templateFolder='templates'
        moduleName='bitplan_webfrontend'
        moduleCode="""
def test():
    return "test result"
        """
        templateCode="""
{{ msg }}     
"""
        self.createPackage(packageFolder, templateFolder, moduleName, moduleCode, templateCode)
        frontend=self.server.enableFrontend('www',self.wcw,debug=False)
        #self.assertEqual(templateFolder,frontend.site.templateFolder)
        self.assertEqual(moduleName,frontend.site.packageName)       
        html,error=frontend.renderTemplate("test.html",msg="Hello world!")
        self.assertIsNone(error)
        self.assertTrue("Hello world!" in html)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
