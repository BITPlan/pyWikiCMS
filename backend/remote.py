"""
Created on 2025-07-21

@author: wf
"""

from dataclasses import dataclass, field
from datetime import datetime
import subprocess
from typing import Dict, Optional, Tuple

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

    def get_size_unit(self, size: int) -> Tuple[str, int]:
        """
        Determine the appropriate unit (GB, MB, kB, B) based on file size.
        """
        if size >= 1024**3:
            unit = "GB", 1024**3
        elif size >= 1024**2:
            unit = "MB", 1024**2
        else:
            unit = "kB", 1024
        return unit

    @property
    def size_str(self)->str:
        unit, divisor = self.get_size_unit(self.size)
        size_str = f"{self.size / divisor:.2f} {unit}"
        return size_str

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

    def run_cmds(self, cmds: Dict[str, str]) -> Dict[str, subprocess.CompletedProcess]:
        """
        Runs a given map of commands
        as long as the return code of the previous command is zero

        Args:
            cmds: key->remote command map

        Returns:
            key->subprocess.CompletedProcess

        Example:
            >>> results = run_cmds({
            ...     'disk': 'df -h',
            ...     'memory': 'free -m',
            ... })
            >>> results['disk'].stdout
            'Filesystem      Size  Used Avail Use% Mounted on...'
        """
        procs = {}
        for key, cmd in cmds.items():
            proc=self.run(cmd)
            procs[key] = proc
            if proc.returncode!=0:
                break
        return procs

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

    def trim_output(self, output: str, max_lines=5, max_len=500) -> str:
        """Trim output to max_lines and max_len, adding truncation notice."""
        if not output:
            return ""
        all_lines = output.splitlines()
        lines=all_lines[:max_lines]
        trimmed = "\n".join(lines)
        if len(trimmed) > max_len:
            trimmed = trimmed[:max_len] + f"... of {len(all_lines)} lines"
        if len(lines) < len(output.splitlines()):
            trimmed += f"\n...[+{len(output.splitlines()) - max_lines} lines]"
        return trimmed


    def run_remote(self, cmd: str, tee=False) -> subprocess.CompletedProcess:
        """Run remote command with concise failure logging."""
        result = self.shell.run(cmd, tee=tee)
        status = "✅" if result.returncode == 0 else "❌"

        log_msg = (
            f"{cmd}\n"
            f"code:{result.returncode}\n"
            f"out:{self.trim_output(result.stdout)}\n"
            f"err:{self.trim_output(result.stderr)}"
        )
        self.log.log(status, "remote", log_msg)
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

    def listdir(self, dirpath: str, wildcard: str = "*", dirs_only: bool = False) -> Optional[list[str]]:
        """
        List directory contents with optional wildcard pattern

        Args:
            dirpath: path to the directory to list
            wildcard: optional wildcard pattern (e.g., "/*.sql")
            dirs_only: if True, list directories only

        Returns:
            List of filenames or None if directory doesn't exist
        """
        dirs_option=""
        if dirs_only:
            dirs_option="d"
            wildcard+="/"
        cmd = f"ls -1{dirs_option} {dirpath}/{wildcard}"
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
