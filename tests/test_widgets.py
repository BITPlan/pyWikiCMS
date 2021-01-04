'''
Created on 2021-01-04

@author: wf
'''
import unittest
from frontend.widgets import Link,Image,Widget

class TestWidgets(unittest.TestCase):


    def setUp(self):
        self.debug=True
        pass


    def tearDown(self):
        pass


    def testWidgets(self):
        '''
        test widget handling
        '''
        widgets=[
            Link("http://www.bitplan.com","BITPlan webPage"),
            Image("http://wiki.bitplan.com/images/wiki/thumb/3/38/BITPlanLogoFontLessTransparent.png/132px-BITPlanLogoFontLessTransparent.png")
        ]
        expectedHtml=[
            "<a href='http://www.bitplan.com'>BITPlan webPage</a>",
            "<img src='http://wiki.bitplan.com/images/wiki/thumb/3/38/BITPlanLogoFontLessTransparent.png/132px-BITPlanLogoFontLessTransparent.png'/>"
            ]
        for i,widget in enumerate(widgets):
            self.assertTrue(isinstance(widget,Widget))
            html=widget.render()
            if self.debug:
                print(html)
            self.assertEqual(expectedHtml[i],html)
            self.assertEqual(expectedHtml[i],str(widget))
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()