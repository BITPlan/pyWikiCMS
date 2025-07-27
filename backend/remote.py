"""
Created on 2025-07-21

@author: wf
"""

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from basemkit.persistent_log import Log
from basemkit.shell import Shell
from basemkit.yamlable import lod_storable


@lod_storable
class Tool:
    """tool configuration."""

    name: Optional[str] = (
        None  # Tool identifier name will be set from dict keys if this tools is part of Tools
    )
    version_cmd: Optional[str] = None  # Command to check tool version
    description: Optional[str] = None  # Tool description text
    wikidata_id: Optional[str] = None  # Wikidata entity identifier
    install_cmd: Optional[str] = None  # Installation command for apt/default
    install_mac: Optional[str] = None  # Installation command for macOS
    post_install_mac: Optional[str] = None  # Post-installation command for macOS


@lod_storable
class Tools:
    """
    assembly of tools
    """

    tools: Dict[str, Tool] = field(default_factory=dict)

    @classmethod
    def of_yaml(cls, yaml_path: str) -> "Tools":
        """Load tools from YAML file."""
        tools = cls.load_from_yaml_file(yaml_path)
        return tools


@dataclass
class Stats:
    filepath: str
    size: int
    mtime_int: int
    permissions: str
    owner: str
    group: str

    @classmethod
    def of_stats(cls, filepath: str, result_stdout: str) -> "Stats":
        """
        Create Stats object from stat command output

        Args:
            filepath: the path of the file these stats are for
            result_stdout: raw output from stat command

        Returns:
            Stats object
        """
        parts = result_stdout.strip().split()
        stats_obj = cls(
            filepath=filepath,
            size=int(parts[0]),
            mtime_int=int(parts[1]),
            permissions=parts[2],
            owner=parts[3],
            group=parts[4],
        )
        return stats_obj

    @property
    def is_directory(self) -> bool:
        """
        Check if the file path represents a directory

        Returns:
            True if directory, False otherwise
        """
        is_directory = self.permissions.startswith("d")
        return is_directory

    @property
    def basename(self) -> str:
        """
        Get the basename (filename) from the filepath

        Returns:
            Filename without directory path
        """
        filename = self.filepath.split("/")[-1]
        return filename

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

    @property
    def age_secs(self) -> float:
        """
        Get age of file in secs from current time

        Returns:
            Age in days as float
        """
        current_time = datetime.now()
        age_secs = (current_time - self.mtime_timestamp).total_seconds()
        return age_secs

    @property
    def age_days(self) -> float:
        """
        Get age of file in days from current time

        Returns:
            Age in days as float
        """
        age_days = self.age_secs / 86400.0
        return age_days


class Remote:
    """
    Provides remote services for
    a given server and potentially a docker container
    """

    def __init__(self, host: str, container: Optional[str] = None, timeout: int = 5):
        """
        Constructor

        Args:
            host: The hostname of the server to connect to
            container: Optional docker container name
            timeout: the timeout for the command
        """
        self.host = host
        self.container = container
        self.shell = Shell()
        self.timeout = timeout
        self.log = Log()
        self.ssh_options = (
            f"-o ConnectTimeout={self.timeout}  -o StrictHostKeyChecking=no {self.host}"
        )

    def run(self, cmd: str, tee: bool = False) -> subprocess.CompletedProcess:
        """
        run the given command remotely
        """
        remote_cmd = f"ssh  {self.ssh_options}"
        if self.container:
            remote_cmd += f" docker exec {self.container}"

        remote_cmd += f' "{cmd}"'
        result = self.run_remote(remote_cmd, tee=tee)
        return result

    def run_remote(
        self, remote_cmd: str, tee: bool = False
    ) -> subprocess.CompletedProcess:
        """
        run the given remote command
        """
        result = self.shell.run(remote_cmd, tee=tee)
        if result.returncode != 0:
            self.log.log("❌", "remote", remote_cmd)
        else:
            self.log.log("✅", "remote", remote_cmd)
        return result

    def scp_from(
        self, remote_path: str, local_path: str
    ) -> subprocess.CompletedProcess:
        """
        Copy file from remote host to local path using scp

        Args:
            remote_path: full path to the remote file
            local_path: full destination path on local machine

        Returns:
            subprocess.CompletedProcess result
        """
        scp_cmd = f"scp {self.ssh_options}:{remote_path} {local_path}"
        return self.run_remote(scp_cmd)

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
            stats_obj = Stats.of_stats(filepath, result.stdout)
        return stats_obj

    def listdir(self, dirpath: str, wildcard: str = "*") -> Optional[list[str]]:
        """
        List directory contents with optional wildcard pattern

        Args:
            dirpath: path to the directory to list
            wildcard: optional wildcard pattern (e.g., "/*.sql")

        Returns:
            List of filenames or None if directory doesn't exist
        """
        cmd = f"ls -1 {dirpath}/{wildcard}"
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
