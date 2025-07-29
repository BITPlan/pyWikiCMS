"""
Created on 2025-07-28

@author: wf
"""

import unittest

from basemkit.basetest import Basetest

from backend.server import Servers
from backend.sql_backup import SqlBackup


class TestSqlBackup(Basetest):
    """
    test remote access
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.servers = Servers.of_config_path()

    def genSqlBackups(self, title: str):
        for server in self.servers.servers.values():
            if self.debug:
                print(f"testing Sql Backup {title} for {server.name}")
            sql_backup = SqlBackup(backup_host=server.hostname, verbose=self.debug)
            yield server, sql_backup

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testSqlBackup(self):
        """
        test sqlbackup handling
        """
        # Create SqlBackup instances for the servers
        for server, sql_backup in self.genSqlBackups("version and show databases"):
            sql_backup.get_version()
            if self.debug:
                print(f"✅ Database version {sql_backup.version} on {server.name}")
            if sql_backup.version and server.has_sqldb:
                proc = sql_backup.run_show_databases_command()
                if self.debug:
                    print(
                        f"exit code: {proc.returncode} on {server.name}\nstdout:{proc.stdout}\n{proc.stderr}"
                    )
                db_list = sql_backup.list_all_databases()
                if self.debug:
                    print(f"found {len(db_list)} databases")
                sql_backup.show_backups()
