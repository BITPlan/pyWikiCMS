"""
Created on 2025-07-21

@author: wf
"""

import socket
import unittest

from basemkit.basetest import Basetest

from backend.remote import Remote


class TestRemote(Basetest):
    """
    test remote access
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def genTestRemotes(self):
        test_cases = (
            ("localhost",),
            ("r.bitplan.com",),
        )

        for (host,) in test_cases:
            remote = Remote(host=host)
            yield host, remote

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
                    print(f"Modified: {stats.modified_iso}")
                    remote.log.dump()
                self.assertIsNotNone(stats, f"Stats should not be None for {filepath}")
                self.assertIsInstance(stats.size, int)
                self.assertIsInstance(stats.mtime, int)
                self.assertIsInstance(stats.ctime, int)
                self.assertIsInstance(stats.permissions, str)
                self.assertIsInstance(stats.owner, str)
                self.assertIsInstance(stats.group, str)

    def testLocalMode(self):
        """
        test remote localmode
        """
        test_file = "/etc/hosts"
        hostname = socket.gethostname()
        for hostname in [hostname, "localhost"]:
            remote = Remote(hostname)
            self.assertTrue(remote.is_local)
            stats = remote.get_file_stats(test_file)
            debug = True
            if debug:
                print(
                    f"{test_file}:created: {stats.created_iso} modified: {stats.modified_iso}{stats.size_str} {stats.age_days:.2f} days old"
                )

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def test_avail_check(self):
        """
        test avail_check functionality
        """
        for host, remote in self.genTestRemotes():
            timestamp = remote.avail_check()
            if self.debug:
                print(f"Host: {host}")
                print(f"Timestamp: {timestamp}")
                print(f"Platform: {remote._platform}")
                print(f"UID: {remote.uid}")
                print(f"GID: {remote.gid}")
                print(f"Is local: {remote.is_local}")

            self.assertIsNotNone(timestamp, f"Timestamp should not be None for {host}")
            self.assertIsNotNone(remote._platform, f"Platform should be set for {host}")
            self.assertIsNotNone(remote.uid, f"UID should be set for {host}")
            self.assertIsNotNone(remote.gid, f"GID should be set for {host}")

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def test_copy_string_to_file(self):
        """
        test copy_string_to_file functionality
        """
        test_lines = ["Line 1", "Line 2", "Line 3"]
        test_content = "\n".join(test_lines)
        test_file = "/tmp/test_copy_string.txt"
        for host, remote in self.genTestRemotes():
            proc = remote.copy_string_to_file(test_content, test_file)
            self.assertEqual(
                proc.returncode, 0, f"copy_string_to_file failed on {host}"
            )

            # Read back the content
            lines = remote.readlines(test_file)
            self.assertEqual(test_lines, lines)
