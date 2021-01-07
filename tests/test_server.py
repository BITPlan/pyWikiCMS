'''
Created on 2021-01-06

@author: wf
'''
import unittest
import socket
from frontend.server import Server

class TestServer(unittest.TestCase):
    '''
    test the server specifics
    '''


    def setUp(self):
        self.debug=True
        pass


    def tearDown(self):
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
            print (server.hostname)
            print (socket.gethostbyname('swa.bitplan.com'))
            
        self.assertTrue("Tux" in logo)
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()