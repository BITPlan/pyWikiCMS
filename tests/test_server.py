'''
Created on 2021-01-06

@author: wf
'''
from frontend.server import Server
from ngwidgets.basetest import Basetest

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
            print(f"platform logo is {logo}")
            print (server.uname)
            print (f"{server.hostname}({server.ip})")
            
        self.assertTrue("Tux" in logo)
        pass
