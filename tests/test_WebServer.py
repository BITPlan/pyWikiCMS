'''
Created on 2020-07-11

@author: wf
'''
import unittest
import frontend.webserver 

from tests.test_WikiCMS import TestWikiCMS
class TestWebServer(unittest.TestCase):
    ''' see https://www.patricksoftwareblog.com/unit-testing-a-flask-application/ '''

    def setUp(self):
        wikiId='or'
        wikiuser=TestWikiCMS.getSMW_WikiUser(wikiId)
        if wikiuser is not None:
            app=frontend.webserver.app
            app.config['TESTING'] = True
            app.config['WTF_CSRF_ENABLED'] = False
            app.config['DEBUG'] = False
            self.app = app.test_client()
            self.debug=True
            frontend.webserver.appWrap.initFrontend(wikiId)
 
        pass

    def tearDown(self):
        pass

    def testWebServer(self):
        ''' test the WebServer '''
        queries='/test','/{Illegal}'
        for query in queries:
            response=self.app.get(query)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data is not None)
            html=response.data.decode()
            if self.debug:
                print(html)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
