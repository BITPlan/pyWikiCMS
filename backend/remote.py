"""
Created on 2025-07-21

@author: wf
"""
from dataclasses import dataclass
import subprocess
from typing import Optional
from datetime import datetime
from basemkit.persistent_log import Log
from basemkit.shell import Shell


@dataclass
class Stats:
    size:int
    mtime_int: int
    permissions:str
    owner:str
    group:str

    @classmethod
    def of_stats(cls, result_stdout: str) -> 'Stats':
        """
        Create Stats object from stat command output

        Args:
            result_stdout: raw output from stat command

        Returns:
            Stats object
        """
        parts = result_stdout.strip().split()
        stats_obj = cls(
            size=int(parts[0]),
            mtime_int=int(parts[1]),
            permissions=parts[2],
            owner=parts[3],
            group=parts[4]
        )
        return stats_obj

    @property
    def is_directory(self) -> bool:
        """
        Check if the file path represents a directory

        Returns:
            True if directory, False otherwise
        """
        is_directory=self.permissions.startswith('d')
        return is_directory

    @property
    def mtime_iso(self) -> str:
        """
        Get modification time as ISO format string

        Returns:
            ISO formatted datetime string
        """
        dt = datetime.fromtimestamp(self.mtime_int)
        iso_str = dt.isoformat()
        return iso_str

    @property
    def mtime_timestamp(self) -> datetime:
        """
        Get modification time as datetime object

        Returns:
            datetime object
        """
        timestamp_obj = datetime.fromtimestamp(self.mtime_int)
        return timestamp_obj

class Remote:
    """
    Provides remote services for
    a given server and potentially a docker container
    """

    def __init__(self, host:str, container: Optional[str] = None,  timeout:int=5):
        """
        Constructor

        Args:
            host: The hostname of the server to connect to
            container: Optional docker container name
            timeout: the timeout for the command
        """
        self.host=host
        self.container = container
        self.shell = Shell()
        self.timeout=timeout
        self.log=Log()

    def run(self,cmd:str,tee:bool=False)-> subprocess.CompletedProcess:
        """
        run the given command remotely
        """
        remote_cmd=f"ssh -o ConnectTimeout={self.timeout}  -o StrictHostKeyChecking=no {self.host} "
        if self.container:
            remote_cmd+=f"docker exec {self.container} "
        remote_cmd+=f'"{cmd}"'
        result = self.shell.run(remote_cmd, tee=tee)
        if result.returncode != 0:
            self.log.log("❌", "remote",remote_cmd)
        else:
            self.log.log("✅", "remote",remote_cmd)
        return result

    def get_output(self, cmd: str) -> Optional[str]:
        """
        Run command and return stripped stdout or None if failed

        Args:
            cmd: command to run

        Returns:
            Stripped stdout or None if command failed
        """
        result = self.run(cmd)
        output = None
        if result.returncode == 0:
            output = result.stdout.strip()
        return output

    def ssh_able(self) -> Optional[datetime]:
        """
        Returns current timestamp if SSH to server is possible, otherwise None.
        """
        result = self.run("echo ok")
        timestamp = None
        if result.returncode == 0 and "ok" in result.stdout:
            timestamp = datetime.now()
        return timestamp

    def get_file_stats(self, filepath: str) -> Optional[Stats]:
        """
        Get file statistics for the given filepath

        Args:
            filepath: path to the file to check

        Returns:
            Stats object or None if file doesn't exist
        """
        cmd = f"stat -c '%s %Y %A %U %G' {filepath}"
        result = self.run(cmd)
        stats_obj = None
        if result.returncode == 0:
            stats_obj = Stats.of_stats(result.stdout)
        return stats_obj

    def listdir(self, dirpath: str) -> Optional[list[str]]:
        """
        List directory contents for the given directory path

        Args:
            dirpath: path to the directory to list

        Returns:
            List of filenames or None if directory doesn't exist
        """
        cmd = f"ls -1 {dirpath}"
        result = self.run(cmd)
        files = None
        if result.returncode == 0:
            files = result.stdout.splitlines()
        return files

    def readlines(self, filepath: str) -> Optional[list[str]]:
        """
        Read lines from the given filepath

        Args:
            filepath: path to the file to read

        Returns:
            List of lines or None if file doesn't exist
        """
        cmd = f"cat {filepath}"
        result = self.run(cmd)
        lines = None
        if result.returncode == 0:
            lines = result.stdout.splitlines()
        return lines
