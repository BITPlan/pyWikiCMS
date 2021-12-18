'''
Created on 2020-12-27

@author: wf
'''
import unittest
from frontend.wikicms import Frontend
from tests.test_webserver import TestWebServer
import getpass
from tests.basetest import Basetest

class TestFrontend(Basetest):
    '''
    test the frontend
    '''

    def setUp(self):
        Basetest.setUp(self)
        self.server=TestWebServer.initServer()
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
        
    def testIssue19(self):
        '''
        https://github.com/BITPlan/pyWikiCMS/issues/19
        editsection filter should keep other span's untouched #19
        '''
        unfiltered="""<span class="mw-editsection">editsection</span><span class='image'>image section</span>"""
        frontend=self.server.enableFrontend('cr')
        filtered=frontend.doFilter(unfiltered,["editsection"])
        #print(filtered)
        self.assertTrue("""<span class="image">image section</span>""" in str(filtered))     
        
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
            
    def testToReveal(self):
        '''
        test reveal handling
        '''
        wikihtml="""
        <!DOCTYPE html>
        <html>
          <body>
             <div>
        <h2><span id="⌘⌘_Slide1"></span><span class="mw-headline" id=".E2.8C.98.E2.8C.98_Slide1">⌘⌘ Slide1</span><span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=RevealTest&amp;action=edit&amp;section=1" title="Edit section: ⌘⌘ Slide1">edit</a><span class="mw-editsection-bracket">]</span></span></h2>
<p>Content for slide 1
</p>
<h2><span id="⌘⌘_Slide2"></span><span class="mw-headline" id=".E2.8C.98.E2.8C.98_Slide2">⌘⌘ Slide2</span><span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=RevealTest&amp;action=edit&amp;section=2" title="Edit section: ⌘⌘ Slide2">edit</a><span class="mw-editsection-bracket">]</span></span></h2>
<p>Content for slide 2
</p>    
                </div>
            </body>
        <html>"""
        frontend=self.server.enableFrontend('www')
        html=frontend.toReveal(wikihtml)
        if self.debug:
            print(html)
        
    def testFixHtml(self):
        '''
        test that hrefs, images src, srcset videos and objects are
        modified from local-absolute urls to ones with "www"
        '''
        frontend=self.server.enableFrontend('www')
        pageTitle,content,error=frontend.getContent("Welcome")
        if error is not None:
            print(error)
            self.fail(error)
        self.assertEqual(pageTitle,"Welcome")
        if self.debug:
            print(content)
        
        self.assertFalse('''href="/index.php''' in content)
        self.assertTrue('''href="/www/index.php''' in content)
        self.assertFalse('''src="/images''' in content)
        self.assertTrue('''src="/www/images''' in content)
        self.assertFalse('''srcset="/images''' in content)
        self.assertTrue('''srcset="/www/images''' in content)
        pass
        
 

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()