'''
Created on 2021-03-14

@author: wf
'''
import unittest
import xml.sax
import lxml.etree as etree
from io import StringIO
from tests.basetest import Basetest

class InsertSections(xml.sax.handler.ContentHandler):
    '''
    ContentHandler for test
    '''
    def __init__(self,debug=False):
        self.debug=debug
        pass
    
    def startElement(self, name, attrs):
        if self.debug:
            print (name,attrs)

    def endElement(self, name):
        pass

class TestParser(Basetest):
    '''
    test different parser approaches
    '''

    def setUp(self):
        Basetest.setUp(self)
        self.html="""
        <!DOCTYPE html>
        <html>
          <body>
             <div>
        <h2><span id="⌘⌘_Slide1"></span><span class="mw-headline" id=".E2.8C.98.E2.8C.98_Slide1">⌘⌘ Slide1</span><span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=RevealTest&amp;action=edit&amp;section=1" title="Edit section: ⌘⌘ Slide1">edit</a><span class="mw-editsection-bracket">]</span></span></h2>
<p>Content for slide 1</p>
<h2><span id="⌘⌘_Slide2"></span><span class="mw-headline" id=".E2.8C.98.E2.8C.98_Slide2">⌘⌘ Slide2</span><span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=RevealTest&amp;action=edit&amp;section=2" title="Edit section: ⌘⌘ Slide2">edit</a><span class="mw-editsection-bracket">]</span></span></h2>
<p>Content for slide 2</p>    
                </div>
            </body>
        </html>"""
        pass
   
    def testSax(self):
        '''
        test sax parser
        '''
        handler = InsertSections(debug=False)
        xml.sax.parseString(self.html,handler)
        pass
    
    def testLxml(self):
        '''
        test html parser
        '''
        #parser=etree.HTMLParser()
        tree=etree.parse(StringIO(self.html))
        self.assertTrue(tree is not None)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()