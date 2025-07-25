"""
Created on 2020-07-27

@author: wf
"""

# from wikibot.smw import SMWClient
from basemkit.basetest import Basetest

from frontend.wikicms import WikiFrontend
from tests.smw_access import SMWAccess


class TestWikiCMS(Basetest):
    """
    test the Mediawiki based Content Management System
    """

    def setUp(self):
        Basetest.setUp(self)
        pass

    def tearDown(self):
        pass

    def testWikiCMS(self):
        """test CMS access"""
        wikiclient = SMWAccess.getSMW_Wiki("wiki")
        pageTitle = "Main Page"
        page = wikiclient.getPage(pageTitle)
        text = page.text()
        debug = self.debug
        # debug = True
        if debug:
            print(text)
        self.assertTrue("Joker" in text)
        pass

    def test_extract_site_and_path(self):
        """
        Test splitting the path into site and path.
        """
        # Test paths and their expected results.
        paths = ["admin/", "or/test"]
        expected_results = [("admin", "/"), ("or", "/test")]

        for index, test_path in enumerate(paths):
            # Extract site and path using the Webserver method.
            site, path = WikiFrontend.extract_site_and_path(test_path)

            # If debugging is enabled, print the results.
            if getattr(self, "debug", False):
                print(f"Site: {site}, Path: {path}")

            # Get the expected site and path.
            expected_site, expected_path = expected_results[index]

            # Assert that the results match the expectations.
            self.assertEqual(expected_site, site)
            self.assertEqual(expected_path, path)
