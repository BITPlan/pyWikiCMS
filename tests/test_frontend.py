'''
Created on 2020-12-27

@author: wf
'''
import unittest
from frontend.wikicms import Frontend
from tests.test_webserver import TestWebServer
import os

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
        
    def createPackage(self,packageFolder,templateFolder,moduleName,moduleCode,templateCode):
        moduleFolder="%s/%s" % (packageFolder,moduleName)
        os.makedirs(moduleFolder,exist_ok=True)
        absTemplateFolder="%s/%s" % (moduleFolder,templateFolder)
        os.makedirs(absTemplateFolder,exist_ok=True)
        modulePath="%s/__init__.py" % moduleFolder 
        print(moduleCode,file=open(modulePath,"w"))
        templatePath="%s/test.html" % (absTemplateFolder)
        print(templateCode,file=open(templatePath,"w"))
        
    def testIssue14Templates(self):
        '''
        test template handling
        '''
        packageFolder='/tmp/www.wikicms'
        templateFolder='templates'
        moduleName='bitplan'
        moduleCode="""
def test():
    pass
        """
        templateCode="""
{{ msg }}        
"""
        self.createPackage(packageFolder, templateFolder, moduleName, moduleCode, templateCode)
        frontend=self.server.enableFrontend('www')
        #self.assertEqual(templateFolder,frontend.site.templateFolder)
        self.assertEqual(moduleName,frontend.site.packageName)       
        html=frontend.renderTemplate("test.html",{"msg":"Hello world!"})
        self.assertTrue("Hello world!" in html)
        
    def testIssue14(self):
        '''
        test Allow to use templates specified in Wiki
        https://github.com/BITPlan/pyWikiCMS/issues/14
        '''
        # see e.g. http://wiki.bitplan.com/index.php/Property:Frame
        frontend=self.server.enableFrontend('wiki')
        pageTitle="Feedback"
        frame=frontend.getFrame(pageTitle)
        self.assertEqual("Contact",frame)
        html=frontend.getContent(pageTitle)
        print(html) 
        
    def testIssue15(self):
        '''
        test Filter "edit" section buttons 
        
        see https://github.com/BITPlan/pyWikiCMS/issues/15
        
        '''
        frontend=self.server.enableFrontend('cr')
        unfiltered="""<span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=...;action=edit&amp;section=T-1" title="Edit section: ">edit</a><span class="mw-editsection-bracket">]</span></span>"""
        filtered=frontend.filterEditSections(unfiltered)
        if self.debug:
            print(filtered)      
        self.assertFalse('''<span class="mw-editsection">''' in filtered)
        pageTitle,content,error=frontend.getContent('Issue15')
        self.assertEqual("Issue15",pageTitle)
        self.assertIsNone(error)
        if self.debug:
            print(content)
        self.assertFalse('''<span class="mw-editsection">''' in content)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()