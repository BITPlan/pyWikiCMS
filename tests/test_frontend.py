'''
Created on 2020-12-27

@author: wf
'''
import unittest
from frontend.WikiCMS import Frontend

class TestFrontend(unittest.TestCase):


    def setUp(self):
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


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()