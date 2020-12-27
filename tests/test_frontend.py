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
        for route in routes:
            pageTitle=frontend.wikiPage(route)
            if self.debug:
                print (pageTitle)
            
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()