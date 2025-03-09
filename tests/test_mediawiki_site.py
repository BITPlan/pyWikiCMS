"""
Created on 2025-03-09

@author: wf
"""
from ngwidgets.basetest import Basetest
from frontend.mediawiki_site import MediaWikiSite

class TestMediawikiSite(Basetest):
    """
    test MediaWikiSite functionality
    """

    def setUp(self, debug=True, profile=True):
        """
        Set up the test case.

        Args:
            debug (bool): If True, show debug information
            profile (bool): If True, enable profiling
        """
        Basetest.setUp(self, debug=debug, profile=profile)

    def test_mediawiki_site(self):
        """
        Test the MediaWikiSite version checking functionality.

        Tests version checking against different wiki installations.
        """
        # List of wiki URLs and their expected versions
        # Format: (wiki_url, expected_version)
        wiki_test_cases = [
            ("http://playground-mw.bitplan.com:9180/index.php","1."),
            ("http://wiki.bitplan.com/index.php", "1.35.5"),
            ("https://en.wikipedia.org/wiki", "1.4")
        ]

        # Run tests for each wiki URL
        for wiki_url, expected_version in wiki_test_cases:
            with self.subTest(wiki_url=wiki_url):
                # Create MediaWikiSite instance
                wiki_site = MediaWikiSite(wiki_url,debug=self.debug)

                # Get the actual version
                actual_version = wiki_site.check_version()

                # Check if the version meets expectations
                # Using startswith to handle patch version differences
                self.assertTrue(
                    actual_version.startswith(expected_version),
                    f"Expected version starting with {expected_version} but got {actual_version}"
                )

                if self.debug:
                    print(f"{wiki_url}: {actual_version}")