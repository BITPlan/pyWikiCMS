'''
Created on 2025-07-29

@author: wf
'''
import unittest

from backend.wikibackup import WikiBackup
from basemkit.basetest import Basetest
from wikibot3rd.wikiuser import WikiUser


class TestWikiBackup(Basetest):
    """
    test remote access
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testWikiBackup(self):
        """
        test backup
        """
        contexts = WikiUser.ofWikiId("contexts", lenient=True)
        wiki_backup = WikiBackup(contexts)
        self.assertTrue(wiki_backup.exists())