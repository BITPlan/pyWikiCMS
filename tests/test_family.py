'''
Created on 2021-01-01

@author: wf
'''
import unittest
from frontend.family import LocalWiki

class TestFamily(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testGetSetting(self):
        '''
        get getting a setting from the local settings
        '''
        lWiki=LocalWiki("wgt.bitplan.com")
        lWiki.settingLines=['''$wgLogo = "/images/wgt/thumb/3/35/Heureka-wgt.png/132px-Heureka-wgt.png";''']
        logo=lWiki.getSetting("wgLogo")
        self.assertTrue(logo.startswith("/images/wgt"))
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()