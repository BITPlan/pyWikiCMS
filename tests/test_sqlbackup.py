"""
Created on 2025-07-28

@author: wf
"""

import unittest

from backend.server import Servers
from backend.sql_backup import SqlBackup
from basemkit.basetest import Basetest
from basemkit.shell import ShellResult


class TestSqlBackup(Basetest):
    """
    test remote access
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.servers = Servers.of_config_path()

    def genSqlBackups(self, title: str):
        """
        yield server and sql backup information
        """
        for server in self.servers.servers.values():
            if self.debug:
                print(f"testing Sql Backup {title} for {server.name}")
            sql_backup = SqlBackup(
                backup_host=server.hostname,
                mysql_root_script=server.mysql_root_script,
                mysql_dump_script=server.mysql_dump_script,
                verbose=self.debug)
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

    def check_sqlrestore(self,sql_backup,db_name:str="test_backup",table:str="t1"):
        """
        test sqlrestore handling with a small one-row table
        """
        # ensure dirs and tmp are ready for backup
        sql_backup.remote.run(f"sudo mkdir -p {sql_backup.today_dir}")
        sql_backup.init()

        # create tiny dataset
        sql_backup.run_mysql_root_command(f"DROP DATABASE IF EXISTS {db_name}")
        rc = sql_backup.run_mysql_root_command(f"CREATE DATABASE {db_name}")
        self.assertEqual(0, rc.returncode, rc.stderr)

        rc = sql_backup.run_mysql_root_command(
            f"CREATE TABLE {db_name}.{table} (id INT PRIMARY KEY, value INT)"
        )
        self.assertEqual(0, rc.returncode, rc.stderr)

        rc = sql_backup.run_mysql_root_command(
            f"INSERT INTO {db_name}.{table} (id, value) VALUES (1, 42)"
        )
        self.assertEqual(0, rc.returncode, rc.stderr)

        # perform full backup
        bproc = sql_backup.backup_database(db_name, full=True)
        self.assertEqual(0, bproc.returncode, bproc.stderr)

        # verify backup file exists
        backup_path = str(sql_backup.get_backup_path(db_name, sql_backup.today_dir, full=True))
        self.assertIsNotNone(sql_backup.remote.get_file_stats(backup_path), f"missing: {backup_path}")

        # remove DB to require restore
        rc = sql_backup.run_mysql_root_command(f"DROP DATABASE IF EXISTS {db_name}")
        self.assertEqual(0, rc.returncode, rc.stderr)

        # enable pv only if available (optional)
        pv_available = sql_backup.remote.run("command -v pv").returncode == 0
        sql_backup.progress = pv_available

        # restore uses today’s full backup when backup_path=None
        rproc = sql_backup.restore_database(database_name=db_name, backup_path=None, force=False)
        self.assertEqual(0, rproc.returncode, rproc.stderr)

        # verify data is back
        q = (
            f'SELECT COUNT(*) AS c FROM {db_name}.{table} '
            f"WHERE id=1 AND value=42"
        )
        sel = sql_backup.run_mysql_root_command(q,as_script=True)
        self.assertEqual(0, sel.returncode, sel.stderr)
        # mysql -e output: header + value; last non-empty line should be the count
        lines = [ln.strip() for ln in sel.stdout.splitlines() if ln.strip()]
        self.assertTrue(lines, "no output from SELECT")
        count_str = lines[-1]
        self.assertEqual("1", count_str, f"unexpected count output: {sel.stdout}")

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testMyqlRootAccess(self):
        """
        test mysql root access
        """
        for server, sql_backup in self.genSqlBackups("version and show databases"):
            sql_backup.get_version()
            if self.debug:
                print(f"✅ Database version {sql_backup.version} on {server.name}")
            if sql_backup.version and server.has_sqldb:
                sql_cmd="SELECT 1;"
                proc = sql_backup.run_mysql_root_command(sql_cmd)
                if self.debug:
                    sh_result=ShellResult(proc,proc.returncode==0)
                    print(f"{sql_cmd}:{sh_result}{proc.stdout}{proc.stderr}")
                self.assertEqual(proc.returncode, 0, f"MySQL root access failed on {server.name}")


    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testSqlRestore(self):
        """
        test sqlrestore handling
        """
        # Create SqlBackup instances for the servers
        for server, sql_backup in self.genSqlBackups("version and show databases"):
            sql_backup.get_version()
            if self.debug:
                print(f"✅ Database version {sql_backup.version} on {server.name}")
            if sql_backup.version and server.has_sqldb:
                db_name:str="test_backup"
                self.check_sqlrestore(sql_backup,db_name=db_name)
                sql_backup.grant_permissions(password="justSomeTestPassword!")
                # cleanup
                sql_backup.run_mysql_root_command(f"DROP DATABASE IF EXISTS {db_name}")
