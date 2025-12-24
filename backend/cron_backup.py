"""
Created on 2025-12-23

@author: wf
"""

import sys
import traceback
from argparse import ArgumentParser
from datetime import date, datetime
from pathlib import Path

from basemkit.base_cmd import BaseCmd
from basemkit.shell import Shell
from expirebackups.expire import Expiration, ExpireBackups

from backend.sql_backup import SqlBackup


class CronBackup(BaseCmd):
    """
    Backup to be performed by entries in crontab.
    Combines SQL database backup and backup expiration functionality.
    """

    def __init__(self, version):
        """
        Initialize CronBackup with version information

        Args:
            version: Version metadata object
        """
        super().__init__(version)
        self.backup_dir = None
        self.log_file = None
        self.container = None
        self.full_backup = False
        self.today = date.today().isoformat()
        self.shell = None

    def add_arguments(self, parser: ArgumentParser):
        """
        Add CronBackup specific arguments to the parser

        Args:
            parser (ArgumentParser): The parser to add arguments to
        """
        # Add standard BaseCmd arguments first
        super().add_arguments(parser)

        # Backup operation selection
        parser.add_argument(
            "-e", "--expire", action="store_true", help="run backup expiration rules"
        )
        parser.add_argument(
            "-b", "--backup", action="store_true", help="run backup process"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="run all operations (expiration + backup)",
        )
        parser.add_argument("--full", action="store_true", help="run in full mode")
        parser.add_argument(
            "-p",
            "--progress",
            action="store_true",
            help="Show progress bars for operations",
        )
        # Backup configuration
        parser.add_argument(
            "--backup-dir",
            default="/var/backup/sqlbackup",
            help="backup directory path [default: %(default)s]",
        )
        parser.add_argument(
            "--log-file",
            default=f"/var/log/sqlbackup/sqlbackup-{self.today}.log",
            help="log file path [default: %(default)s]",
        )
        # database settings
        # the database container running the mysql instance
        parser.add_argument(
            "--container",
            default="family-db",
            help="docker container name [default: %(default)s]",
        )
        parser.add_argument(
            "--mysql-root-cmd",
            help="command for MySQL root access (e.g., 'mysqlr -cn family-db')",
        )
        parser.add_argument(
            "--mysqldump-cmd",
            help="command for mysqldump (e.g., 'mysqlr -cn family-db --dump')",
        )
        parser.add_argument(
            "--database",
            default="all",
            help="database to backup [default: %(default)s]",
        )

        # Expiration rules
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="number of daily backups to keep [default: %(default)s]",
        )
        parser.add_argument(
            "--weeks",
            type=int,
            default=6,
            help="number of weekly backups to keep [default: %(default)s]",
        )
        parser.add_argument(
            "--months",
            type=int,
            default=8,
            help="number of monthly backups to keep [default: %(default)s]",
        )
        parser.add_argument(
            "--years",
            type=int,
            default=4,
            help="number of yearly backups to keep [default: %(default)s]",
        )

        # Shell configuration
        parser.add_argument(
            "--profile", help="shell profile to source (e.g., ~/.zprofile)"
        )

    def log(self, message: str):
        """
        Log a message to the log file and optionally to stdout

        Args:
            message (str): Message to log
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        if self.verbose:
            print(log_entry.strip())

        try:
            # Ensure log directory exists
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a") as f:
                f.write(log_entry)
        except Exception as e:
            if not self.quiet:
                print(f"Warning: Could not write to log file: {e}", file=sys.stderr)

    def handle_exception(self, title: str, ex: Exception):
        """
        Handle the given exception

        Args:
            title (str): Title/context of the exception
            ex (Exception): The exception to handle
        """
        self.log(f"{title} failed: {ex}")
        if self.debug:
            self.log(traceback.format_exc())

    def run_expire(self) -> int:
        """
        Run backup expiration rules using ExpireBackups module

        Returns:
            int: 0 on success, non-zero on failure
        """
        exit_code = 0
        self.log("Running expiration rules...")

        try:
            expiration = Expiration(
                days=self.args.days,
                weeks=self.args.weeks,
                months=self.args.months,
                years=self.args.years,
                minFileSize=1,
                debug=self.debug,
            )

            expire_backups = ExpireBackups(
                rootPath=str(self.backup_dir),
                baseName="sql_backup",
                ext=".tgz",
                expiration=expiration,
                dryRun=not self.force,
                debug=self.debug,
            )

            expire_backups.doexpire(
                withDelete=self.force, show=self.verbose, showLimit=None
            )

            self.log("Expiration rules completed")

        except Exception as ex:
            self.handle_exception("Expiration", ex)
            exit_code = 1

        return exit_code

    def create_archive(self) -> int:
        """
        Create tar.gz archive of today's backup using Shell

        Returns:
            int: 0 on success, non-zero on failure
        """
        exit_code = 1
        date_str = datetime.now().strftime("%Y-%m-%d")
        archive_name = f"sql_backup.{date_str}.tgz"
        archive_path = self.backup_dir / archive_name

        self.log(f"Creating archive {archive_name}...")

        try:
            # Build tar command
            cmd_parts = [
                "tar",
                "--create",
                "--gzip",
                "-p",
                f"-f {archive_path}",
                f"-C {self.backup_dir}",
                "today",
            ]

            if self.verbose:
                cmd_parts.insert(1, "-v")

            cmd = " ".join(cmd_parts)

            # Run with Shell and tee output if verbose
            result = self.shell.run(cmd, text=True, debug=self.debug, tee=self.verbose)

            if result.returncode == 0:
                self.log(f"Archive {archive_name} created successfully")
                if self.verbose and result.stdout:
                    self.log(f"Archive output:\n{result.stdout}")
                exit_code = 0
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.log(f"Archive creation failed: {error_msg}")
                if self.debug:
                    self.log(f"Stdout: {result.stdout}")
                exit_code = 1

        except Exception as ex:
            self.handle_exception("Archive creation", ex)
            exit_code = 1

        return exit_code

    def run_backup(self) -> int:
        """
        Run database backup using SqlBackup module

        Returns:
            int: 0 on success, non-zero on failure
        """
        exit_code = 1
        self.log("Starting backup...")

        try:
            # Ensure backup directory exists
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Construct MySQL commands
            mysql_root_cmd = self.args.mysql_root_cmd
            if mysql_root_cmd is None:
                # Default: use mysqlr wrapper with container
                mysql_root_cmd = f"mysqlr --no-tty -cn {self.container}"

            mysqldump_cmd = self.args.mysqldump_cmd
            if mysqldump_cmd is None:
                mysqldump_cmd = f"mysqlr --no-tty -cn {self.container} --dump"

            # Create SqlBackup instance
            sql_backup = SqlBackup(
                backup_user="backup",
                backup_host="localhost",
                backup_dir=str(self.backup_dir),
                mysql_root_script=mysql_root_cmd,
                mysql_dump_script=mysqldump_cmd,
                verbose=self.verbose,
                debug=self.debug,
                progress=self.args.progress,
            )

            # Initialize if needed
            sql_backup.init()

            # Perform backup
            errors = sql_backup.perform_backup(
                database=self.args.database, full=self.full_backup
            )

            if errors == 0:
                self.log("Backup completed successfully")
                # Create archive
                exit_code = self.create_archive()
            else:
                self.log(f"Backup failed with {errors} error(s)")
                exit_code = 1

        except Exception as ex:
            self.handle_exception("Backup", ex)
            exit_code = 1

        return exit_code

    def handle_args(self, args) -> bool:
        """
        Handle parsed arguments and execute operations

        Args:
            args: Parsed argument namespace

        Returns:
            bool: True if argument was handled and no further processing is required
        """
        handled = True

        # Let BaseCmd handle standard arguments first
        base_handled = super().handle_args(args)
        if base_handled:
            handled = True
        else:
            # Initialize Shell with profile from args
            self.shell = Shell.ofArgs(args)

            # Store configuration
            self.backup_dir = Path(args.backup_dir)
            self.log_file = Path(args.log_file)
            self.container = args.container
            self.full_backup = args.full

            # Determine what operations to run
            run_expire = args.expire or args.all
            run_backup = args.backup or args.all

            # If no operation specified, show help
            if not (run_expire or run_backup):
                self.parser.print_help()
                handled = True
            else:
                self.exit_code = 0

                # Run operations in order: expire first, then backup
                if run_expire:
                    result = self.run_expire()
                    if result != 0:
                        self.exit_code = result

                if run_backup and self.exit_code == 0:
                    result = self.run_backup()
                    if result != 0:
                        self.exit_code = result

                handled = True

        return handled


def main(argv=None):
    """
    Main entry point for CronBackup

    Args:
        argv: Command line arguments

    Returns:
        int: Exit code (0 = success, non-zero = failure)
    """

    # Create a version object
    class Version:
        name = "CronBackup"
        version = "0.1.1"
        description = (
            "Database backup with expiration management to be started from cron"
        )
        updated = "2025-12-23"
        doc_url = "https://github.com/WolfgangFahl/pyWikiCMS"

    exit_code = CronBackup.main(Version(), argv)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
