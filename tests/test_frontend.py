'''
Created on 2020-12-27

@author: wf
'''
import unittest
from frontend.wikicms import Frontend
from tests.test_webserver import TestWebServer

class TestFrontend(unittest.TestCase):
    '''
    test the frontend
    '''

    def setUp(self):
        self.debug=False
        self.frontends=TestWebServer.initFrontends()
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
        frontend=Frontend('sharks')
        self.frontends.enable(frontend)
        frontend.open()
        url="/images/wiki/thumb/6/62/IMG_0736_Shark.png/400px-IMG_0736_Shark.png"
        self.assertTrue(frontend.needsProxy(url))
        imageResponse=frontend.proxy(url)
        self.assertFalse(imageResponse is None)
        self.assertEqual("200 OK",imageResponse.status)
        self.assertEqual(79499,len(imageResponse.data))
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()