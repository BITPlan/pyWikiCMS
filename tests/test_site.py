"""
Created on 2021-01-01

@author: wf
"""

import unittest

from basemkit.basetest import Basetest

from backend.server import Servers


class TestSite(Basetest):
    """
    test wiki
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.servers = Servers.of_config_path()

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testLogo(self):
        """
        test fixing BITPlan wiki family style logo references with a site subpath
        """
        wiki = self.servers.wikis_by_hostname.get("wiki.bitplan.com")
        logoFile = wiki.getLogo()
        if self.debug:
            print(logoFile)
        self.assertFalse("/md/" in logoFile)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testStatusCode(self):
        """
        test getting the status code for the a wiki
        """
        wiki = self.servers.wikis_by_hostname.get("wiki.bitplan.com")
        server=self.servers.servers.get("q")
        self.assertIsNotNone(server)
        wiki.configure_of_settings(server,"/var/www/mediawiki/sites/wiki.bitplan.com/LocalSettings.php")
        statusCode = wiki.getStatusCode(5.0)
        self.assertEqual(200, statusCode)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testGetSetting(self):
        """
        get getting a setting from the local settings
        """
        wiki = self.servers.wikis_by_hostname.get("wgt.bitplan.com")
        wiki.settingLines = [
            """$wgLogo = "/images/wgt/thumb/3/35/Heureka-wgt.png/132px-Heureka-wgt.png";"""
        ]
        logo = wiki.getSetting("wgLogo")
        self.assertTrue(logo.startswith("/images/wgt"))
        pass
