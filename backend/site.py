"""
Created on 2021-01-01

@author: wf
"""

from dataclasses import field, dataclass
import re
import socket
from typing import Optional

from backend.remote import Remote
from basemkit.yamlable import lod_storable
import requests


@dataclass
class Site:
    """
    an Apache Site
    """
    name: str
    # if container is set the site is provided by a docker container
    container: Optional[str]=None
    apache_config: Optional[str] = None
    ip: str = field(default="?", init=False)
    url: Optional[str] = field(default=None, init=False)

    # Non-persistent calculated fields
    remote: Remote = field(default=None, init=False, repr=False)
    hostname: str = field(default=None,init=False,repr=True)


    def __post_init__(self):
        """
        initialize
        """
        self._resolve_ip()

    @classmethod
    def state_symbol(cls, b: bool) -> str:
        """
        return the symbol for the given boolean state b

        Args:
            b(bool): the state to return a symbol for

        Returns:
            ✅ for True and ❌ for false
        """
        symbol = "✅" if b else "❌"
        return symbol

    def init_remote(self):
        self.remote = Remote(host=self.hostname, container=self.container)

    def _resolve_ip(self) -> None:
        """Resolve IP address for the site name"""
        try:
            self.ip = socket.gethostbyname(self.name)
        except Exception:
            self.ip = "?"

@lod_storable
class WikiSite(Site):
    """
    A MediaWiki Site
    """
    wikiId: Optional[str] = None
    database: Optional[str] = None
    defaultPage: str = "Main Page"
    lang: str = "en"

    # LocalWiki properties
    family: Optional[object] = field(default=None, init=False)
    localSettings: Optional[str] = field(default=None, init=False)
    logo: Optional[str] = field(default=None, init=False)
    dbUser: Optional[str] = field(default=None, init=False)
    dbPassword: Optional[str] = field(default=None, init=False)
    scriptPath: str = field(default="", init=False)
    statusCode: int = field(default=-1, init=False)
    settingLines: list = field(default_factory=list, init=False)

    # Non-persistent calculated fields
    debug: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        """Initialize"""
        super().__post_init__()
        pass

    def configure_of_settings(self, family = None, localSettings: str = None) -> None:
        """
        Configure this site from the given settings

        Args:
            family: WikiFamily instance
            localSettings: path to LocalSettings.php
        """
        self.family = family
        self.localSettings = localSettings

        if self.localSettings:
            self._load_settings()
            self._configure_from_settings()

    def _load_settings(self) -> None:
        """Load settings from LocalSettings.php file"""
        self.settingLines = self.family.remote.readlines(self.localSettings)

    def _configure_from_settings(self) -> None:
        """Configure site properties from loaded settings"""
        self.logo = self.getSetting("wgLogo")
        database_setting = self.getSetting("wgDBname")
        if database_setting:
            self.database = database_setting
        self.url = self.getSetting("wgServer")
        self.dbUser = self.getSetting("wgDBuser")
        self.dbPassword = self.getSetting("wgDBpassword")
        self.scriptPath = self.getSetting("wgScriptPath") or ""

        if self.url:
            self.url = f"{self.url}{self.scriptPath}"
            self.statusCode = self.getStatusCode()

    def getStatusCode(self, timeout: float = 0.5) -> int:
        """
        Get the HTTP status code for the site URL

        Args:
            timeout: maximum time to wait for response

        Returns:
            HTTP status code or -1 if timeout/error
        """
        status_code = -1
        try:
            response = requests.get(self.url, verify=False, timeout=timeout)
            status_code = response.status_code
        except Exception:
            pass
        return status_code

    def getSetting(self, varName: str) -> Optional[str]:
        """
        Extract setting value from LocalSettings.php lines

        Args:
            varName: variable name to extract

        Returns:
            Variable value or None if not found
        """
        pattern = rf'[^#]*\${varName}\s*=\s*"(.*)"'
        for line in self.settingLines:
            match = re.match(pattern, line)
            if match:
                value = match.group(1)
                return value
        return None

    def getLogo(self) -> Optional[str]:
        """
        Get local filesystem path to logo file

        Returns:
            Logo file path or None if not available
        """
        if not self.logo:
            return None

        logo_path = self.logo
        logo_path = logo_path.replace("$wgResourceBasePath", "")
        site_id = self.name.split(".")[0]
        logo_path = logo_path.replace(f"/images/{site_id}/", "/images/")

        if logo_path.startswith("/") and self.family:
            logo_file = f"{self.family.sitedir}/{self.name}{logo_path}"
            return logo_file
        return None


@lod_storable
class FrontendSite(Site):
    """
    a frontend site - backed by a WikiSite
    """
    wikiId:str = "wiki"
    defaultPage: str = "Main Page"
    enabled: bool=False;

    # non persistent field
    wikisite: WikiSite = field(default=False, init=False, repr=False)
