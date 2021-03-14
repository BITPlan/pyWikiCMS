'''
Created on 2020-12-27

@author: wf
'''
import unittest
from frontend.wikicms import Frontend
from tests.test_webserver import TestWebServer
import os
import tempfile
import getpass

class TestFrontend(unittest.TestCase):
    '''
    test the frontend
    '''

    def setUp(self):
        self.debug=False
        self.server=TestWebServer.initServer()
        pass

    def tearDown(self):
        pass
    
    @staticmethod
    def inPublicCI():
        '''
        are we running in a public Continuous Integration Environment?
        '''
        return getpass.getuser() in [ "travis", "runner" ];
    

    def testWikiPage(self):
        '''
        test the route to page translation
        '''
        frontend=Frontend('cr')
        routes=['/index.php/File:Link.png']
        expectedList=['File:Link.png']
        for i,route in enumerate(routes):
            pageTitle=frontend.wikiPage(route)
            if self.debug:
                print (pageTitle)
            expected=expectedList[i]
            self.assertEqual(expected,pageTitle)
            
        pass
    
    def testProxy(self):
        '''
        test the proxy handling
        '''
        frontend=self.server.enableFrontend('sharks')
        url="/images/wiki/thumb/6/62/IMG_0736_Shark.png/400px-IMG_0736_Shark.png"
        self.assertTrue(frontend.needsProxy(url))
        imageResponse=frontend.proxy(url)
        self.assertFalse(imageResponse is None)
        self.assertEqual("200 OK",imageResponse.status)
        self.assertEqual(79499,len(imageResponse.data))
        
    def testIssue18(self):
        '''
        https://github.com/BITPlan/pyWikiCMS/issues/18
        image proxying should work #18
        '''
        frontend=self.server.enableFrontend('www')
        url="/images/wiki/thumb/4/42/1738-006.jpg/400px-1738-006.jpg"
        self.assertTrue(frontend.needsProxy(url))
        imageResponse=frontend.render(url)
        self.assertFalse(imageResponse is None)
        self.assertEqual("200 OK",imageResponse.status)
        self.assertEqual(33742,len(imageResponse.data))
        
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
        if TestFrontend.inPublicCI():
            return
        packageFolder='%s/www.wikicms' % tempfile.gettempdir()
        templateFolder='templates'
        moduleName='bitplan_webfrontend'
        moduleCode="""
def test():
    pass
        """
        templateCode="""
{{ msg }}        
"""
        self.createPackage(packageFolder, templateFolder, moduleName, moduleCode, templateCode)
        frontend=self.server.enableFrontend('www',debug=False)
        #self.assertEqual(templateFolder,frontend.site.templateFolder)
        self.assertEqual(moduleName,frontend.site.packageName)       
        html,error=frontend.renderTemplate("test.html",{"msg":"Hello world!"})
        self.assertIsNone(error)
        self.assertTrue("Hello world!" in html)
        
    def testIssue14(self):
        '''
        test Allow to use templates specified in Wiki
        https://github.com/BITPlan/pyWikiCMS/issues/14
        '''
        # see e.g. http://wiki.bitplan.com/index.php/Property:Frame
        frontend=self.server.enableFrontend('www')
        pageTitle="Feedback"
        frame=frontend.getFrame(pageTitle)
        self.assertEqual("Contact",frame)
        html=frontend.getContent(pageTitle)
        if self.debug:
            print(html) 
        
    def testIssue15(self):
        '''
        test Filter "edit" section buttons 
        
        see https://github.com/BITPlan/pyWikiCMS/issues/15
        
        '''
        frontend=self.server.enableFrontend('cr')
        unfiltered="""<span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=...;action=edit&amp;section=T-1" title="Edit section: ">edit</a><span class="mw-editsection-bracket">]</span></span>"""
        filtered=frontend.doFilter(unfiltered,["editsection"])
        if self.debug:
            print(filtered)      
        self.assertFalse('''<span class="mw-editsection">''' in filtered)
        pageTitle,content,error=frontend.getContent('Issue15')
        self.assertEqual("Issue15",pageTitle)
        self.assertIsNone(error)
        if self.debug:
            print(content)
        self.assertFalse('''<span class="mw-editsection">''' in content)
        
    def testIssue17(self):
        '''
        https://github.com/BITPlan/pyWikiCMS/issues/17
        
        filter <html><body><div class="mw-parser-output">
        '''
        frontend=self.server.enableFrontend('cr')
        unfiltered="""<html><body><div class="mw-parser-output">content</div></body></html>"""
        filtered=frontend.doFilter(unfiltered,"mw-parser-output")
        #self.debug=True
        if self.debug:
            print(filtered)    
        self.assertFalse("<html>" in filtered)
        self.assertFalse("<body>" in filtered)
        pageTitle,content,error=frontend.getContent('Issue17')
        self.assertIsNone(error)
        self.assertEqual("Issue17",pageTitle)
        if self.debug:
            print(content)
 

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()