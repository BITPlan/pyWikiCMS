"""
Created on 2025-07-21

@author: wf
"""
import glob
import grp
import os
import pwd
import socket
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
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
    mtime: int
    ctime: int
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
            mtime=int(parts[1]),
            permissions=parts[2],
            owner=parts[3],
            group=parts[4],
            ctime=int(parts[5]),
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
    def size_str(self) -> str:
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
    def modified_iso(self) -> str:
        """
        Get modification time as ISO format string

        Returns:
            ISO formatted datetime string
        """
        modified_iso = None
        modified = self.modified_timestamp
        if modified:
            modified_iso = modified.isoformat()
        return modified_iso

    @property
    def modified_timestamp(self) -> datetime:
        """
        Get modification time as datetime object

        Returns:
            datetime object
        """
        modified = datetime.fromtimestamp(self.mtime)
        return modified

    @property
    def created_timestamp(self) -> Optional[datetime]:
        """
        Get creation (ctime) time as datetime object

        Returns:
            datetime object if ctime_int is set, otherwise None
        """
        created = datetime.fromtimestamp(self.ctime)
        return created

    @property
    def created_iso(self) -> Optional[str]:
        """
        Get creation (ctime) time as ISO format string

        Returns:
            ISO formatted string if ctime_int is set, otherwise None
        """
        created_iso = None
        created = self.created_timestamp
        if created:
            created_iso = created.isoformat()
        return created_iso

    @property
    def age_secs(self) -> float:
        """
        Get age of file in secs from current time

        Returns:
            Age in days as float
        """
        current_time = datetime.now()
        age_secs = (current_time - self.modified_timestamp).total_seconds()
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
    Provides remote services for a given server and potentially a docker container,
    with optimized local execution when the server is the machine this service runs on
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
        self._here_host = socket.gethostname()
        self.is_local = False
        self._ip = None
        self._platform = None
        try:
            host_ip = socket.gethostbyname(host)
            self._ip = host_ip
            local_ips = socket.gethostbyname_ex(self._here_host)[2]
            self.is_local = (
                host_ip in local_ips or host_ip.startswith("127.") or host_ip == "::1"
            )
            if self.is_local:
                self._platform = sys.platform
        except Exception as _ex:
            # keep None defaults
            pass
        self.container = container
        self.shell = Shell()
        self.timeout = timeout
        self.log = Log()
        self.ssh_options = (
            f"-o ConnectTimeout={self.timeout}  -o StrictHostKeyChecking=no {self.host}"
        )

    def __str__(self):
        text= f"{self.host}{self.symbol}"
        return text

    @property
    def symbol(self)->str:
        host_kind = "🐳" if self.container else "  " # 2 spaces for width of whale
        os_symbol = {
            "linux": "🐧",
            "darwin": "🍏",
            "win32": "🪟"
        }.get(self._platform, "❓")
        symbol= f"{os_symbol}{host_kind}"
        return symbol

    def get_ip(self) -> str:
        """
        """
        if self._ip is None:
            self._ip = self.get_output("hostname -I | awk '{print $1}'")
        return self._ip

    def get_platform(self) -> str:
        if self._platform is None:
            self.avail_check()
        return self._platform

    def run_cmds(self,
        cmds: Dict[str, str],
        stop_on_error:bool=True,
        as_single_cmd: bool=False) -> Dict[str, subprocess.CompletedProcess]:
        """
        Runs a given map of commands
        as long as the return code of the previous command is zero

        Args:
            cmds: key->remote command map
            stop_on_error: if True do not continue when an error occurs
            as_single_cmd: if True combine all commands with ';' separator to a single long command

        Returns:
            key->subprocess.CompletedProcess with a single "all" key if as_single_cmd is True

        Example:
            >>> results = run_cmds({
            ...     'disk': 'df -h',
            ...     'memory': 'free -m',
            ... })
            >>> results['disk'].stdout
            'Filesystem      Size  Used Avail Use% Mounted on...'
        """
        procs = {}
        if as_single_cmd:
            combined_cmd = "; ".join(cmds.values())
            proc=self.run(combined_cmd)
            procs["all"]=proc
        else:
            for key, cmd in cmds.items():
                proc = self.run(cmd)
                procs[key] = proc
                if proc.returncode != 0:
                    if stop_on_error:
                        break
                    else:
                        continue
        return procs

    def run_cmds_as_single_cmd(self, cmds: Dict[str, str], stop_on_error: bool = True) -> subprocess.CompletedProcess:
        """
        Run commands as single combined command and return the result directly

        Args:
            cmds: key->remote command map
            stop_on_error: if True do not continue when an error occurs

        Returns:
            subprocess.CompletedProcess result of combined command
        """
        procs = self.run_cmds(cmds, stop_on_error=stop_on_error, as_single_cmd=True)
        proc = procs["all"]
        return proc

    def run(self, cmd: str, tee: bool = False) -> subprocess.CompletedProcess:
        """
        Run the given command locally or remotely (optionally inside a container)

        Args:
            cmd: The shell command to execute
            tee: Whether to tee output

        Returns:
            CompletedProcess: the result of the command
        """
        full_cmd = cmd
        if not self.is_local:
            full_cmd = f"ssh  {self.ssh_options}"
        if self.container:
            full_cmd += f" docker exec {self.container}"

        full_cmd += f' "{cmd}"'
        result = self.run_remote(full_cmd, tee=tee)
        return result

    def trim_output(self, output: str, max_lines=5, max_len=500) -> str:
        """Trim output to max_lines and max_len, adding truncation notice."""
        if not output:
            return ""
        all_lines = output.splitlines()
        lines = all_lines[:max_lines]
        trimmed = "\n".join(lines)
        if len(trimmed) > max_len:
            trimmed = trimmed[:max_len] + f"... of {len(all_lines)} lines"
        if len(lines) < len(output.splitlines()):
            trimmed += f"\n...[+{len(output.splitlines()) - max_lines} lines]"
        return trimmed

    def run_remote(self, cmd: str, tee=False) -> subprocess.CompletedProcess:
        """
        Execute a command with optional output teeing.

        The command may include ssh and docker exec parts to enable remote or
        containerized execution. Local execution is also possible if applicable.

        Args:
            cmd: The full command string to execute.
            tee: If True, tee the command's output to stdout/stderr.

        Returns:
            CompletedProcess: The result of the executed command, including output and return code.
        """
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

    def rsync(self, source_path: str, target_path: str, marker_file: str,
          message: str, update: bool = False, uid: Optional[int] = None,
          gid: Optional[int] = None, do_mkdir: bool = True,
          do_permissions: bool = True) -> subprocess.CompletedProcess:
        """
        Args:
            source_path: Source path (must include server)
            target_path: Target path (must be local)
            marker_file: file to check for existence as indicator for sync completion
            message: Log message for sync operation
            update: Force update even if sentinel_file exists
            uid: User ID for ownership (optional)
            gid: Group ID for ownership (optional)
            do_mkdir: Whether to create directory if missing
            do_permissions: Whether to change ownership/permissions
        """
        marker_path = f"{target_path}/{marker_file}"
        marker_stats = self.get_file_stats(marker_path)
        needs_sync = marker_stats is None or update

        if not needs_sync:
            self.log.log("✅", "sync", f"{marker_path} already exists")
            return subprocess.CompletedProcess([], 0, "", "")

        target_uid = uid if uid is not None else getattr(self, 'uid', None)
        target_gid = gid if gid is not None else getattr(self, 'gid', None)
        should_set_permissions = do_permissions and target_uid and target_gid

        if do_mkdir:
            needs_mkdir=self.get_file_stats(target_path) is None
            if needs_mkdir:
                proc=self.run(f"sudo mkdir -p {target_path}")
                if proc.returncode!=0:
                    return proc

        if should_set_permissions:
            perm_cmds = {
                'chown_pre': f"sudo chown {target_uid}:{target_gid} {target_path}",
                'chmod_pre': f"sudo chmod g+w {target_path}"
            }
            proc = self.run_cmds_as_single_cmd(perm_cmds)
            if proc.returncode != 0:
                return proc

        rsync_cmd = f"rsync -avz --no-perms --omit-dir-times {source_path}/* {target_path}"
        proc = self.run(rsync_cmd)

        if should_set_permissions and proc.returncode == 0:
            chown_cmd=f"sudo chown -R {target_uid}:{target_gid} {target_path}"
            self.run(chown_cmd)

        status = "✅" if proc.returncode == 0 else "❌"
        self.log.log(status, "sync", f"synching {message}")

        return proc


    def scp_copy(self, source_path: str, target_path: str) -> subprocess.CompletedProcess:
        """
        Copy a file using scp between any combination of local or remote paths.
        This method is executed locally, not on the remote.

        Args:
            source_path: Source path (may include user@host:)
            target_path: Target path (may include user@host:)

        Returns:
            subprocess.CompletedProcess result
        """
        scp_cmd = f"scp -p {source_path} {target_path}"
        proc = self.run(scp_cmd)
        return proc


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

    def avail_check(self) -> Optional[datetime]:
        """
        Returns current timestamp if local server or if SSH to server is possible.
        Also sets platform info and uid/gid if available, otherwise returns None.
        """
        timestamp = None
        if self.is_local:
            self._platform = sys.platform
            self.uid = os.getuid()
            self.gid = os.getgid()
            timestamp = datetime.now()
        else:
            result = self.run("python3 -c 'import sys, os; print(sys.platform, os.getuid(), os.getgid())'")
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                self._platform = parts[0]
                self.uid = parts[1]
                self.gid = parts[2]
                timestamp = datetime.now()
        return timestamp

    def get_remote_file_stats(self, filepath: str) -> Optional[Stats]:
        """
        Get file statistics for the given filepath remotely

        Args:
            filepath: path to the file to check

        Returns:
            Stats object or None if file doesn't exist
        """
        cmd = f"stat -c '%s %Y %A %U %G %Z' {filepath}"
        result = self.run(cmd)
        stats_obj = None
        if result.returncode == 0:
            stats_obj = Stats.of_stats(filepath, result.stdout)
        return stats_obj

    def get_local_file_stats(self, filepath: str) -> Optional[Stats]:
        """
        Get file statistics for the given filepath remotely

        Args:
            filepath: path to the file to check

        Returns:
            Stats object or None if file doesn't exist
        """
        stats = None
        try:
            st = os.stat(filepath)
            size = st.st_size
            mtime = int(st.st_mtime)
            ctime = int(st.st_ctime)
            permissions = "-" + stat.filemode(st.st_mode)[1:]
            owner = pwd.getpwuid(st.st_uid).pw_name
            group = grp.getgrgid(st.st_gid).gr_name
            stats = Stats(
                filepath=filepath,
                size=size,
                mtime=mtime,
                ctime=ctime,
                permissions=permissions,
                owner=owner,
                group=group,
            )
        except Exception:
            pass
        return stats

    def get_file_stats(self, filepath: str) -> Optional[Stats]:
        """
        Get file statistics for the given filepath remotely

        Args:
            filepath: path to the file to check

        Returns:
            Stats object or None if file doesn't exist
        """
        stats = (
            self.get_local_file_stats(filepath)
            if self.is_local
            else self.get_remote_file_stats(filepath)
        )
        return stats

    def get_local_dir_list(self, dirpath: str, wildcard: str, dirs_only: bool) -> Optional[list[str]]:
        """
        List directory contents locally with optional wildcard and dir filter.
        """
        files = None
        try:
            pattern = os.path.join(dirpath, wildcard)
            entries = glob.glob(pattern)
            if dirs_only:
                entries = [entry for entry in entries if os.path.isdir(entry)]
            files = [os.path.basename(entry) for entry in entries]
        except Exception:
            files = None
        return files


    def get_remote_dir_list(
        self, dirpath: str, wildcard: str = "*", dirs_only: bool = False
    ) -> Optional[list[str]]:
        """
        List directory contents with optional wildcard pattern

        Args:
            dirpath: path to the directory to list
            wildcard: optional wildcard pattern (e.g., "/*.sql")
            dirs_only: if True, list directories only

        Returns:
            List of filenames or None if directory doesn't exist
        """
        dirs_option = ""
        if dirs_only:
            dirs_option = "d"
            wildcard += "/"
        cmd = f"ls -1{dirs_option} {dirpath}/{wildcard}"
        result = self.run(cmd)
        files = None
        if result.returncode == 0:
            files = result.stdout.splitlines()
        return files

    def listdir(self, dirpath: str, wildcard: str = "*", dirs_only: bool = False) -> Optional[list[str]]:
        """
        List directory contents with optional wildcard pattern.

        Args:
            dirpath: path to the directory to list
            wildcard: optional wildcard pattern (e.g., "*.sql")
            dirs_only: if True, list directories only

        Returns:
            List of filenames or None if directory doesn't exist
        """
        if self.is_local:
            return self.get_local_dir_list(dirpath, wildcard, dirs_only)
        else:
            return self.get_remote_dir_list(dirpath, wildcard, dirs_only)


    def readlines(self, filepath: str) -> Optional[list[str]]:
        """
        Read lines from the given filepath

        Args:
            filepath: path to the file to read

        Returns:
            List of lines or None if file doesn't exist
        """
        lines = None
        if self.is_local:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
            except Exception:
                lines = None
        else:
            cmd = f"cat {filepath}"
            result = self.run(cmd)
            if result.returncode == 0:
                lines = result.stdout.splitlines()
        return lines

