"""
Created on 2025-07-21

@author: wf
"""

import unittest

from basemkit.basetest import Basetest
from wikibot3rd.wikiuser import WikiUser

from backend.remote import Remote
from backend.wikibackup import WikiBackup


class TestRemote(Basetest):
    """
    test remote access
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testStats(self):
        """
        test remote stats
        """
        test_cases = (
            ("r.bitplan.com", None, "/etc/apache2/sites-available/crm.conf"),
            (
                "r.bitplan.com",
                "smartcrm-java",
                "/root/.jpa/Production/com.bitplan.smartCRM.xml",
            ),
        )

        for host, container, filepath in test_cases:
            with self.subTest(host=host, container=container, filepath=filepath):
                remote = Remote(host=host, container=container)
                stats = remote.get_file_stats(filepath)
                if self.debug:
                    print(f"Host: {host}, Container: {container}")
                    print(f"File: {filepath}")
                    print(stats)
                    print(f"Modified: {stats.mtime_iso}")
                    remote.log.dump()
                self.assertIsNotNone(stats, f"Stats should not be None for {filepath}")
                self.assertIsInstance(stats.size, int)
                self.assertIsInstance(stats.mtime_int, int)
                self.assertIsInstance(stats.permissions, str)
                self.assertIsInstance(stats.owner, str)
                self.assertIsInstance(stats.group, str)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testLocalMode(self):
        """
        test remote localmode
        """
        contexts = WikiUser.ofWikiId("contexts", lenient=True)
        wiki_backup = WikiBackup(contexts)
        self.assertTrue(wiki_backup.exists())
        #self.assertTrue(wiki_backup.has_git())
