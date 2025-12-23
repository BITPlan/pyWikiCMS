#!/usr/bin/env python3
"""
SQLBackup - MySQL/MariaDB database backup utility
Converted from bash script to Python using Remote class

@author: wf
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from basemkit.persistent_log import Log
from tqdm import tqdm

from backend.remote import Remote


class SqlBackup:
    """
    MySQL/MariaDB database backup manager
    """

    def __init__(
        self,
        backup_user: str = "backup",
        backup_host: str = "localhost",
        backup_dir: str = "/var/backup/sqlbackup",
        mysql_root_script = "sudo mysql -u root",
        mysql_dump_script = "sudo mysqldump -u root",
        verbose: bool = False,
        debug: bool = False,
        progress: bool = False,
    ):
        """
        Initialize SQLBackup instance

        Args:
            backup_user: Database backup user name
            backup_host: Database host name
            login_path: MySQL login path name
            backup_dir: Base backup directory path
            mysql_root_script: the script to use for mysql root access
            mysql_dump_script: the script to use for mysql dump (with root permissions)
            verbose: Enable verbose output
            debug: Enable debug output
            progress: show progress
        """
        self.backup_user = backup_user
        self.backup_host = backup_host
        self.backup_dir = Path(backup_dir)
        self.mysql_root_script=mysql_root_script
        self.mysql_dump_script=mysql_dump_script
        self.verbose = verbose
        self.debug = debug
        self.progress = progress
        self.remote = Remote(host=backup_host)
        self.today_dir = self.backup_dir / "today"
        self.tmp_dir = self.backup_dir / "tmp"

        self.version = None
        self.log = Log()

    def get_version(self) -> str:
        """
        get the full version string
        """
        if self.version is None:
            result = self.remote.run("mysql --version")
            if result.returncode == 0:
                self.version = result.stdout
        return self.version

    def run_mysql_root_command(self, cmd: str, as_script: bool = False) -> subprocess.CompletedProcess:
        """
        Run the given MySQL command as root.
        - as_script=False: pipe a single line (canonical echo)
        - as_script=True : create .sql file and run it
        """
        if as_script:
            sql_file = self.remote.gen_tmp("sql_cmd.sql")
            self.remote.copy_string_to_file(cmd, sql_file)
            proc = self.remote.run(f"{self.mysql_root_script} < {sql_file}")
            self.remote.run(f"rm -f {sql_file}")  # cleanup
        else:
            proc = self.remote.run(f"echo '{cmd}' | {self.mysql_root_script}")
        return proc

    def run_show_databases_command(self) -> subprocess.CompletedProcess:
        """
        Execute show databases MySQL command

        Returns:
            subprocess.CompletedProcess result
        """
        if not self.version:
            raise ValueError("get_version must be called first")
        proc=self.run_mysql_root_command("show databases")
        return proc;

    def parse_database_list(self, result) -> List[str]:
        """
        Parse database list from MySQL command result

        Args:
            result: subprocess.CompletedProcess result

        Returns:
            List of database names
        """
        databases = []
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line and line not in [
                    "Database",
                    "information_schema",
                    "performance_schema",
                ]:
                    if not line.startswith("#"):
                        databases.append(line)
        return databases

    def list_all_databases(self) -> List[str]:
        """
        List all databases

        Returns:
            List of database names
        """
        result = self.run_show_databases_command()
        databases = self.parse_database_list(result)
        return databases

    def show_backups(self):
        self.get_version()
        databases = self.list_all_databases()
        for database in databases:
            for full in [False, True]:
                backup_path = self.get_backup_path(database, self.today_dir, full)
                stats = self.remote.get_file_stats(backup_path)
                if stats:
                    age_marker = "✅" if stats.age_days < 1.0 else "❌"
                    print(
                        f"{self.backup_host}:{backup_path} {stats.size_str} {stats.age_days:.2f} d {age_marker}"
                    )

    def get_backup_path(self, database: str, base_path: str, full: bool = False) -> str:
        """
        Generate a backup file path for the given database.

        Args:
            database: Name of the database to back up.
            base_path: Base directory path where the backup should be stored.
            full: If True, generates a path for a full backup. If False, generates a path
                  for an incremental backup. Defaults to False.

        Returns:
            str: The full path for the backup file, including the appropriate file extension.
        """
        postfix = "_full" if full else ""
        db_file = f"{database}{postfix}.sql"
        backup_path = base_path / db_file
        return backup_path

    def backup_database(
        self, database: str, full: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Backup single database

        Args:
            database: Database name to backup
            full: Whether to include table structure

        Returns:
            True if backup successful, False otherwise
        """
        backup_tmp_path = self.get_backup_path(database, self.tmp_dir, full)
        backup_path = self.get_backup_path(database, self.today_dir, full)

        create_option = "" if full else "--no-create-db --no-create-info"
        cmds = {
            "backup": f'{self.mysql_dump_script} --quick --routines {create_option} --skip-add-locks --complete-insert --opt "{database}" > {backup_tmp_path}',
            "move": f"sudo mv {backup_tmp_path} {backup_path}",
            "owner": f"sudo chown {self.backup_user} {backup_path}",
            "permissions": f"sudo chmod 640 {backup_path}",
        }
        procs = self.remote.run_cmds(cmds)
        proc = procs.get("backup")
        return proc

    def restore_database(self, database_name: str, backup_path: str = None, force: bool = False) -> subprocess.CompletedProcess:
        """
        Restore a database from a .sql dump.

        Args:
            database_name: the name of the database
            backup_path: absolute path to the .sql file on backup_host; if None, use today's full backup
            force: drop and recreate the target database before import

        Returns:
            subprocess.CompletedProcess of the restore command
        """
        # resolve backup path
        if backup_path is None:
            backup_path = str(self.get_backup_path(database_name, self.today_dir, full=True))

        # verify backup exists
        if self.remote.get_file_stats(backup_path) is None:
            raise FileNotFoundError(f"backup not found: {backup_path}")

        # prepare database
        if force:
            drop_proc = self.run_mysql_root_command(f"DROP DATABASE IF EXISTS `{database_name}`")
            if drop_proc.returncode != 0:
                raise RuntimeError(f"Failed to drop database {database_name}: {drop_proc.stderr}")

        # create DB only if missing
        exist_cmd= f"USE {database_name}";
        exists_proc = self.run_mysql_root_command(exist_cmd)
        # Non-existence is possible here, MySQL returns:
        # ERROR 1049 (42000) at line 1: Unknown database '...'
        if exists_proc.returncode != 0:
            create_proc = self.run_mysql_root_command(f"CREATE DATABASE {database_name}")
            if create_proc.returncode != 0:
                raise RuntimeError(
                    f"Failed to create database {database_name}: {create_proc.stderr}"
                )

        # restore with optional pv
        if self.progress:
            restore_cmd = f"sudo pv '{backup_path}' | {self.mysql_root_script} {database_name}"
        else:
            restore_cmd = f"sudo mysql -u root {database_name} < '{backup_path}'"

        proc = self.remote.run(restore_cmd)
        return proc



    def perform_backup(self, database: str = "all", full: bool = True) -> int:
        """Perform backups of one or more databases.

        Args:
            database: Name of the database to back up. Defaults to "all" which will
                back up all available databases.
            full: If True, performs a full backup. If False, performs an incremental
                backup. Defaults to True.

        Returns:
            int: The number of failed backups (0 if all were successful).
        """
        self.get_version()
        errors = 0
        if database == "all":
            databases = self.list_all_databases()
        else:
            databases = [database]
        iterator = (
            tqdm(databases, desc=f"{len(databases)} databases") if self.progress else databases
        )
        for database in iterator:
            if self.progress:
                iterator.set_description_str(f"{database}")
            proc = self.backup_database(database, full)
            if proc.returncode != 0:
                errors += 1
        return errors

    def create_backup_archive(self) -> bool:
        """
        Create compressed backup archive

        Returns:
            True if archive created successfully, False otherwise
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        backup_file = f"sql_backup.{date_str}.tgz"
        backup_path = self.backup_dir / backup_file

        verbose_flag = "-v" if self.verbose else ""
        cmd = f"tar --create {verbose_flag} --gzip -p -f {backup_path} -C {self.backup_dir} today"
        result = self.remote.run(cmd)

        success = result.returncode == 0
        if success:
            self.show_result(f"{backup_file} created")

        return success

    def init(self):
        """
        initialize the backup enviroment
        """
        cmds = {
            "create temp dir": f"sudo mkdir -p {self.tmp_dir}",
            "change permissions": f"sudo chmod 777 {self.tmp_dir}",
            "change owner": f"sudo chown {self.backup_user} {self.tmp_dir}",
        }
        self.remote.run_cmds(cmds)

    def grant_permissions(self, password: str) -> subprocess.CompletedProcess:
        """
        Grant database permissions for backup user (no mysql_config_editor; use mysql_root_script)
        """
        grant_sql = (
            f"GRANT SELECT,EXECUTE,PROCESS,SHOW VIEW,SHOW DATABASES,LOCK TABLES "
            f"ON *.* TO '{self.backup_user}'@'{self.backup_host}' IDENTIFIED BY '{password}';"
        )
        proc = self.run_mysql_root_command(grant_sql,as_script=True)
        return proc



def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create command line argument parser

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(description="SQL backup utility for MySQL/MariaDB")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-d", "--debug", action="store_true", help="show debug info")
    parser.add_argument(
        "-f", "--full", action="store_true", help="Full backup with table structure"
    )
    parser.add_argument(
        "-i", "--init", action="store_true", help="Initialize backup environment"
    )
    parser.add_argument("-l", "--list", action="store_true", help="List all databases")
    parser.add_argument("-b", "--backup", action="store_true", help="perform backup")
    parser.add_argument(
        "-p",
        "--progress",
        action="store_true",
        help="Show progress bars for operations",
    )
    parser.add_argument("-hs", "--host", help="Backup host")
    parser.add_argument(
        "-db",
        "--database",
        help="the database to backup 'all' if all databases should be backed up",
        default="all",
    )
    parser.add_argument("--mysql-root-cmd", help="Command for MySQL root access (e.g. 'mysqlr -cn db')")
    parser.add_argument("--mysqldump-cmd", help="Command for mysqldump (e.g. 'mysqlr -cn db --dump')")

    parser.add_argument("-u", "--user", help="Backup user")
    return parser


def main():
    """
    Main entry point for SQLBackup utility
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    backup = SqlBackup(
        backup_user=args.user or "backup",
        backup_host=args.host or "localhost",
        mysql_root_script=args.mysql_root_cmd or "sudo mysql -u root",
        mysql_dump_script=args.mysqldump_cmd or "sudo mysqldump -u root",
        verbose=args.verbose,
        debug=args.debug,
        progress=args.progress,
    )
    exit_code = 0

    if args.list:
        backup.show_backups()

    if args.init:
        success = backup.init()
        if not success:
            exit_code = 1

    if args.backup:
        errors = backup.perform_backup(database=args.database, full=args.full)
        if errors == 0:
            pass
            #    success = backup.create_backup_archive()
        else:
            exit_code = 1
    if args.debug:
        backup.remote.log.dump()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
