'''
Created on 2021-01-06

@author: wf
'''
import unittest
from frontend.server import Server
from tests.basetest import Basetest

class TestServer(Basetest):
    '''
    test the server specifics
    '''

    def setUp(self):
        Basetest.setUp(self)
        pass

    def testServer(self):
        '''
        test server functions
        '''
        server=Server()
        server.platform='linux'
        logo=server.getPlatformLogo()
        if self.debug:
            print("platform logo is %s " % logo)
            print (server.uname)
            print ("%s(%s)" % (server.hostname,server.ip))
            
        self.assertTrue("Tux" in logo)
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()