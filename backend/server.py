"""
Created on 2021-01-06

@author: wf
"""
from dataclasses import field
import datetime
import glob
import os
import re
import socket
from sys import platform
from typing import Dict, Optional

from backend.remote import Remote
from backend.site import Site, WikiSite, FrontendSite
from basemkit.persistent_log import Log
from basemkit.yamlable import lod_storable
import pymysql


@lod_storable
class Server:
    """
    a server that might serve multiple wikis for a wikiFarm
    either in legacy style with a directory layout or with multiple docker
    containers
    """
    name: str
    hostname: str
    admin_user: Optional[str]=None
    admin_password: Optional[str]=None
    purpose: Optional[str]=None
    logo: str = "https://wiki.bitplan.com/images/wiki/6/63/Profiwikiicon.png"
    sqlBackupPath:str = "/var/backup/sqlbackup"
    timeout:int=5 # 5 secs
    sites: Dict[str, Site] = field(default_factory=dict)
    wikis: Dict[str, WikiSite] = field(default_factory=dict)
    frontends: Dict[str,FrontendSite]  = field(default_factory=dict)

    # Non-persistent calculated fields
    sitedir: str = field(default=False,init=False, repr=False)
    actual_hostname: str = field(default="", init=False, repr=False)
    platform: str = field(default="", init=False, repr=False)
    ip: str = field(default="127.0.0.1", init=False, repr=False)
    debug: bool = field(default=False, init=False, repr=False)
    remote: Remote = field(default=None, init=False, repr=False)
    log: Log = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """
        Initialize calculated fields
        """
        self.log=Log()
        self.remote=Remote(self.hostname)

    @classmethod
    def of_yaml(cls, yaml_path: str) -> "Server":
        """Load server configurations from YAML file."""
        server_configs = cls.load_from_yaml_file(yaml_path)
        return server_configs

    def probe_remote(self):
        """
        Probe my properties by remote access

        Args:
            timeout (int): SSH connection timeout in seconds
        """
        # Check if SSH is reachable
        ssh_timestamp = self.remote.ssh_able()

        if ssh_timestamp:
            # Get platform information
            self.platform = self.remote.get_output("python3 -c 'import sys; print(sys.platform)'")

            # Get hostname
            self.hostname = self.remote.get_output("hostname")

            # Get IP address from remote perspective
            self.ip = self.remote.get_output("hostname -I | awk '{print $1}'")

            self.probe_apache_configs()


    def probe_apache_configs(self):
        """
        Probe and set Apache configuration for all sites
        """
        apache_configs = self.remote.get_output("sudo apachectl -S | grep namevhost")
        if apache_configs:
            for line in apache_configs.split('\n'):
                if line.strip():
                    match = re.search(r'namevhost (\S+) \(([^:]+):', line)
                if match:
                    hostname = match.group(1)
                    config_file = match.group(2)
                    for site in self.wikis.values():
                        if site.name in hostname:
                            site.apache_config = config_file

    def probe_local(self, debug: bool = False):
        """
        Probe local system properties

        Args:
            debug (bool): Enable debug output
        """
        self.debug = debug
        self.platform = platform
        uname = os.uname()
        self.actual_hostname = uname[1]
        try:
            self.ip = socket.gethostbyname(socket.getfqdn())
        except Exception as ex:
            if self.debug:
                print(str(ex))
            self.ip = "127.0.0.1"

    def probe_wiki_family(self, sitedir: str = "/var/www/mediawiki/sites") -> list[WikiSite]:
        """
        probe this server for a wiki
        family by scanning sitedir for LocalSettings.php files

        Args:
            sitedir: path to the site definitions directory

        Returns:
            List of WikiSites found
        """
        self.sitedir = sitedir
        wikisites = []

        stats = self.remote.get_file_stats(sitedir)
        if stats is None or not stats.is_directory:
            return wikisites

        site_files = self.remote.listdir(sitedir)
        if site_files is None:
            return wikisites

        for site_file in site_files:
            local_settings_path = f"{sitedir}/{site_file}/LocalSettings.php"
            settings_stats = self.remote.get_file_stats(local_settings_path)

            if settings_stats is not None and not settings_stats.is_directory:
                site_name=site_file
                if site_name not in self.wikis:
                    self.log.log("⚠️", "configure_wiki_family", f"Site {site_name} found but not declared")
                else:
                    site=self.wikis.get(site_name)
                    site.configure_of_settings(family=self, localSettings=local_settings_path)
                    wikisites.append(site)

        return wikisites

    def sqlGetDatabaseUrl(
        self, dbname: str, username: str, password: str, hostname: str = None
    ) -> str:
        """
        get the DatabaseUrl for the given database Name

        Args:
            dbname(str): the name of the database
            username(str): the username
            password(str): the password

        Returns:
            str: the url for sqlAlchemy in rfc1738 format e.g. mysql://dt_admin:dt2016@localhost:3308/dreamteam_db
        """
        # http://docs.sqlalchemy.org/en/latest/dialects/mysql.html
        if hostname is None:
            hostname = self.hostname
        url = "mysql+pymysql://%s:%s@%s/%s" % (username, password, hostname, dbname)
        return url

    def sqlDatabaseExist(
        self, dbname: str, username: str, password: str, hostname: str = None
    ) -> bool:
        """
        Check if the database with the given name exists.

        Args:
            dbname (str): The name of the database.
            username (str): The username.
            password (str): The password.
            hostname (str): The hostname. Defaults to the class's hostname.

        Returns:
            bool: True if the database exists, else False.
        """
        if hostname is None:
            hostname = self.hostname

        connection = None
        try:
            connection = pymysql.connect(
                host=hostname,
                user=username,
                password=password,
                database="information_schema",
                connect_timeout=5,
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT SCHEMA_NAME FROM SCHEMATA WHERE SCHEMA_NAME = %s", (dbname,)
                )
                result = cursor.fetchone()
            return result is not None
        except pymysql.MySQLError:
            return False
        finally:
            if connection:
                connection.close()

    def sqlBackupStateAsHtml(self, dbName):
        """
        get the backup state of the given sql backup

        Args:
           dbName(str): the name of the database to check

        Returns:
            html: backup State html representation
        """
        backupState = self.sqlBackupState(dbName)
        mbSize = backupState["size"] / 1024 / 1024
        mdate = backupState["mdate"]
        isoDate = mdate.strftime("%Y-%m-%d %H:%M:%S") if mdate else ""
        html = "%s %s - %4d MB" % (
            self.stateSymbol(backupState["exists"]),
            isoDate,
            mbSize,
        )
        return html

    def sqlBackupState(self, dbName):
        """
        get the backup state of the given sql backup

        Args:
           dbName(str): the name of the database to check

        Returns:
            dict: backup State

        """
        fullBackup = "%s/today/%s_full.sql" % (self.sqlBackupPath, dbName)
        size = 0
        mdate = None
        exists = os.path.isfile(fullBackup)
        if exists:
            stat = os.stat(fullBackup)
            size = stat.st_size
            mtime = stat.st_mtime
            mdate = datetime.datetime.fromtimestamp(mtime)
        result = {"size": size, "exists": exists, "mdate": mdate}
        return result

    def getPlatformLogo(self) -> str:
        """
        get the logo url for the platform this server runs on

        Returns:
            str: the url of the logo for the current operating system platform
        """
        logos = {
            "aix": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/IBM_AIX_logo.svg/200px-IBM_AIX_logo.svg.png",
            "cygwin": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Cygwin_logo.svg/200px-Cygwin_logo.svg.png",
            "darwin": "https://upload.wikimedia.org/wikipedia/de/thumb/b/b1/MacOS-Logo.svg/200px-MacOS-Logo.svg.png",
            "linux": "https://upload.wikimedia.org/wikipedia/commons/a/af/Tux.png",
            "win32": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Windows_logo_-_2012.svg/200px-Windows_logo_-_2012.svg.png",
            "unknown": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Blue_question_mark.jpg/240px-Blue_question_mark.jpg",
        }
        if self.platform in logos:
            logo = logos[self.platform]
        else:
            logo = logos["unknown"]
        return logo

    def checkApacheConfiguration(self, conf, status="enabled") -> str:
        """
        check the given apache configuration and return an indicator symbol

        Args:
            conf(str): the name of the apache configuration

        Returns:
            a state symbol
        """
        path = f"/etc/apache2/sites-{status}/{conf}.conf"
        confExists = os.path.isfile(path)
        stateSymbol = self.stateSymbol(confExists)
        return stateSymbol

    def as_html(self, logo_size: int = 64) -> str:
        """
        render me as HTML code

        Args:
            logo_size(int): the logo_size to apply
        """
        server = self
        logo_html = ""
        if server.logo is not None:
            logo_html = f"""<td><img src='{server.logo }' alt='{server.name} logo' height='{logo_size}' width='{logo_size}'></td>"""
        html = f"""<table>
<tr>
    <td><img src='{server.getPlatformLogo()}' alt='{server.platform} logo' height='{logo_size}' width='{logo_size}'></td>
    {logo_html}
    <td><span>Welcome to {server.name } ({ server.ip }) { server.purpose }</span><td>
</tr>
</table>
"""
        return html

@lod_storable
class Servers:
    """
    Collection of servers loaded from YAML configuration files
    """
    servers: Dict[str, Server] = field(default_factory=dict)
    # Non-persistent calculated fields
    wikis_by_hostname: Dict[str, WikiSite] = field(default_factory=dict, init=False, repr=False)
    wikis_by_id: Dict[str, WikiSite] = field(default_factory=dict, init=False, repr=False)
    frontends_by_hostname: Dict[str,FrontendSite] = field(default_factory=dict, init=False, repr=False)
    frontends_by_name: Dict[str,FrontendSite] = field(default_factory=dict, init=False, repr=False)
    log: Log = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """
        Initialize calculated fields
        """
        self.log=Log()

    @classmethod
    def of_config_path(cls) -> "Servers":
        """
        Load all servers from YAML files in the config path

        Returns:
            Servers: Container with collection of loaded servers
        """
        servers_instance = cls()
        config_path = cls.get_config_path()
        yaml_pattern = f"{config_path}/*.yaml"
        yaml_files = glob.glob(yaml_pattern)

        for yaml_file in yaml_files:
            server = Server.of_yaml(yaml_file)
            server_name = os.path.basename(yaml_file).replace('.yaml', '')
            servers_instance.servers[server_name] = server

        servers_instance.init()
        return servers_instance

    @classmethod
    def get_config_path(cls) -> str:
        """
        get the path where my config file is located
        Returns:
        path to .wikicms in the homedirectory of the current user
        """
        home_path = os.path.expanduser("~")
        config_path = f"{home_path}/.wikicms"
        if not os.path.isdir(config_path):
            os.makedirs(config_path)
        return config_path

    def init(self) -> None:
        """
        Initialize wikis_by_name dictionary
        from all servers' wikis and set remote
        """
        self.wikis_by_hostname.clear()
        self.wikis_by_id.clear()
        self.frontends_by_hostname.clear()
        self.frontends_by_name.clear()
        for server in self.servers.values():
            for hostname, wiki in server.wikis.items():
                self.wikis_by_hostname[hostname] = wiki
                self.wikis_by_id[wiki.wikiId] =wiki
                wiki.hostname=hostname
                wiki.init_remote()
            for hostname,frontend in server.frontends.items():
                self.frontends_by_hostname[hostname]=frontend
                self.frontends_by_name[frontend.name]=frontend
                frontend.hostname=hostname
                frontend.init_remote()
                if frontend.wikiId in self.wikis_by_id:
                    frontend.wikisite=self.wikis_by_id.get(frontend.wikiId)
                else:
                    msg=f"invalid frontend wikiId {frontend.wikiId}"
                    self.log.log("❌","frontend",msg)
