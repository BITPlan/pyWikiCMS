'''
Created on 2021-03-14

@author: wf
'''
import unittest
import xml.sax
import lxml.etree as etree
from io import StringIO

class InsertSections(xml.sax.handler.ContentHandler):
    def __init__(self):
        pass
    
    def startElement(self, name, attrs):
        print (name,attrs)

    def endElement(self, name):
        pass

        
class Test(unittest.TestCase):


    def setUp(self):
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


    def tearDown(self):
        pass
    
   
    def testSax(self):
        handler = InsertSections()
        xml.sax.parseString(self.html,handler)
        pass
    
    def testLxml(self):
        parser=etree.HTMLParser()
        tree=etree.parse(StringIO(self.html))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()