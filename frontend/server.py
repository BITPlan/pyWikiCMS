"""
Created on 2021-01-06

@author: wf
"""
import datetime
import os
import socket
from pathlib import Path
from sys import platform

from lodstorage.jsonable import JSONAble

from frontend.wikicms import Frontend


class Server(JSONAble):
    """
    a server that might serve multiple wikis for a wikiFarm
    """

    homePath = None

    def __init__(self, debug=False):

        """
        Constructor

        Args:
            storePath(str): the path to load my configuration from (if any)
        """
        self.storage_secret = None
        self.frontendConfigs = None
        self.logo = "https://wiki.bitplan.com/images/wiki/6/63/Profiwikiicon.png"
        self.purpose = ""
        self.reinit(debug)

    def reinit(self, debug=False):
        """
        reinitialize me
        """
        self.debug = debug
        self.platform = platform
        self.uname = os.uname()
        self.name = self.uname[1]
        self.hostname = "?"
        self.ip = "127.0.0.1"
        try:
            self.hostname = socket.getfqdn()
            self.ip = socket.gethostbyname(self.hostname)
        except Exception as ex:
            if self.debug:
                print(str(ex))
            pass
        self.frontends = {}
        self.siteLookup = {}
        defaults = {"sqlBackupPath": "/var/backup/sqlbackup"}
        for key, value in defaults.items():
            if not hasattr(self, key):
                setattr(self, key, value)
        if Server.homePath is None:
            self.homePath = str(Path.home())
        else:
            self.homePath = Server.homePath

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

    def sqlDatabaseExist(self, dbname: str, username: str, password: str, hostname: str = None) -> bool:
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
                cursor.execute("SELECT SCHEMA_NAME FROM SCHEMATA WHERE SCHEMA_NAME = %s", (dbname,))
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

    def enableFrontend(self, siteName: str, appWrap=None, debug: bool = False):
        """
        enable the given frontend

        Args:
            siteName(str): the siteName of the frontend to enable
            appWrap(appWrap): optional fb4 Application Wrapper
        Returns:
            Frontend: the configured frontend
        """
        if self.frontendConfigs is None:
            raise Exception("No frontend configurations loaded yet")
        if siteName not in self.siteLookup:
            raise Exception(f"frontend for site {siteName} not configured yet")
        frontend = Frontend(siteName)
        self.frontends[siteName] = frontend
        config = self.siteLookup[siteName]
        frontend.site.configure(config)
        frontend.site.debug = debug
        frontend.open(appWrap)
        return frontend
        pass

    def getFrontend(self, wikiId):
        """
        get the frontend for the given wikiid

        Args:
            wikiId(str): the wikiId to get the frontend for

        Returns:
            Frontend: the frontend for this wikiId
        """
        return self.frontends[wikiId]

    def load(self):
        """
        load my front end configurations
        """
        storePath = self.getStorePath()
        if os.path.isfile(storePath + ".json"):
            self.restoreFromJsonFile(storePath)
            self.reinit()
            for config in self.frontendConfigs:
                siteName = config["site"]
                self.siteLookup[siteName] = config
        pass

    def getStorePath(self, prefix: str = "serverConfig") -> str:
        """
        get the path where my store files are located
        Returns:
            path to .wikicms in the homedirectory of the current user
        """
        iniPath = self.homePath + "/.wikicms"
        if not os.path.isdir(iniPath):
            os.makedirs(iniPath)
        storePath = f"{iniPath}/{prefix}"
        return storePath

    def store(self):
        if self.frontends is not None:
            storePath = self.getStorePath()
            self.storeToJsonFile(storePath)

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

    def stateSymbol(self, b: bool) -> str:
        """
        return the symbol for the given boolean state b

        Args:
            b(bool): the state to return a symbol for

        Returns:
            ✅ for True and ❌ for false
        """
        symbol = "✅" if b else "❌"
        return symbol

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

    def asHtml(self, logo_size: int = 64) -> str:
        """
        render me as HTML code

        Args:
            logo_size(int): the logo_size to applyå
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
