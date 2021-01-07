'''
Created on 2021-01-01

@author: wf
'''
import unittest
from frontend.family import LocalWiki, WikiFamily

class TestFamily(unittest.TestCase):
    '''
    test wiki family code
    '''

    def setUp(self):
        self.debug=True
        pass


    def tearDown(self):
        pass

    def testLogo(self):
        '''
        test fixing BITPlan wiki family style logo references with a site subpath
        '''
        family=WikiFamily()
        wiki=LocalWiki("md.bitplan.com",family)
        wiki.logo="/images/md/thumb/4/47/BITPlanMd.png/120px-BITPlanMd.png"
        logoFile=wiki.getLogo()
        if self.debug:
            print(logoFile)
        self.assertFalse("/md/" in logoFile)
        

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