"""
Created on 2021-01-01

@author: wf
"""

from dataclasses import dataclass, field
import platform
import re
import socket
from typing import Any, Dict, List, Optional

from backend.remote import Remote
from backend.wikibackup import WikiBackup
from basemkit.yamlable import lod_storable
from frontend.html_table import HtmlTables
from lodstorage.lod import LOD
from mogwai.core import MogwaiGraph
from ngwidgets.widgets import Link
import requests
from tqdm import tqdm
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.wikiuser import WikiUser


@dataclass
class Site:
    """
    an Apache Site
    """
    name: str
    # if container is set the site is provided by a docker container
    container: Optional[str] = None
    apache_config: Optional[str] = None
    ip: str = field(default="?", init=False)
    url: Optional[str] = field(default=None, init=False)

    # Non-persistent calculated fields
    remote: Remote = field(default=None, init=False, repr=False)
    hostname: str = field(default=None, init=False, repr=True)

    def __post_init__(self):
        """
        initialize
        """
        if self.hostname is None:
            self.hostname=self.name
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
        """
        initialize my remote access
        """
        if self.remote is None:
            self.remote = Remote(host=self.hostname, container=self.container)

    def _resolve_ip(self) -> None:
        """Resolve IP address for the site name"""
        try:
            self.ip = socket.gethostbyname(self.name)
        except Exception:
            self.ip = "?"

    def ping(self):
        # https://stackoverflow.com/a/34455969/1497139
        proc=None
        try:
            option="-n" if platform.system().lower()=="windows" else "-c"
            cmd=f"ping {option} 1 -t 1 {self.name}"
            self.init_remote()
            proc=self.remote.shell.run(cmd)
        except Exception as ex:
            pass
        return proc


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

    # Non-persistent and calculated fields
    debug: bool = field(default=False, init=False, repr=False)
    database_setting: str = field(default=None, init=False)
    wiki_url: str = field(default="", init=False)
    show_html: bool = field(default=False, init=False)
    wiki_user: WikiUser = field(default=None, init=False)
    wiki_backup: WikiBackup = field(default=None, init=False)
    _wiki_client: WikiClient = field(default=None, init=False)
    # dgraph related fields
    _node_id: str = field(default=None, init=False)
    row_no: int = field(default=0, init=False)

    def __post_init__(self):
        """Initialize"""
        super().__post_init__()
        pass

    def configure_of_settings(self,family=None,localSettings:str=None) -> None:
        """
        Configure this site from the given settings

        Args:
            family: optional server instance of the family we belong to
            localSettings: path to LocalSettings.php
        """
        if family is not None:
            self.family=family
        if localSettings is not None:
            self.localSettings=localSettings
        if self.family is not None and self.localSettings is None:
            self.localSettings=f"{self.family.sitedir}/{self.hostname}/LocalSettings.php"
        if self.localSettings is None:
            self.localSettings="/var/www/html/LocalSettings.php"

        if self.localSettings:
            self.load_settings()
            if self.settingLines:
                self.configure_from_settings()

    def load_settings(self) -> None:
        """Load settings from LocalSettings.php file"""
        if self.family is not None:
            remote=self.family.remote
        else:
            remote=self.remote
        self.settingLines = remote.readlines(self.localSettings)

    def configure_from_settings(self) -> None:
        """Configure site properties from loaded settings"""
        self.logo = self.getSetting("wgLogo")
        self.database_setting = self.getSetting("wgDBname")
        if self.database is None:
            self.database = self.database_setting
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
        if self.settingLines:
            for line in self.settingLines:
                match = re.match(pattern, line)
                if match:
                    value = match.group(1)
                    return value
        return None

    def init_wikiuser_and_backup(self, wikiUser: WikiUser = None) -> WikiUser:
        """
        initialize my wiki user and wiki_backup
        """
        if wikiUser is None:
            wikiUser = WikiUser.ofWikiId(wikiId=self.wikiId, lenient=True)
        self.wiki_user = wikiUser
        if self.wiki_user:
            self.wiki_url = self.wiki_user.url
        self.wiki_backup = WikiBackup(self.wiki_user)
        return self.wiki_user

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

    @classmethod
    def ofWikiUser(
        cls,
        wiki_user: WikiUser,
        debug: bool = False,
        show_html: bool = False,
    ):
        """
        constructor
        """
        wiki_id = wiki_user.wikiId
        wiki = cls(name=wiki_id, wikiId=wiki_id)
        wiki.init_wikiuser_and_backup(wiki_user)
        wiki.debug = debug
        wiki.show_html = show_html
        return wiki

    @property
    def wiki_client(self) -> WikiClient:
        if not self._wiki_client:
            client = WikiClient.ofWikiUser(self.wiki_user)
            if client.needs_login:
                client.login()
            self._wiki_client = client
        return self._wiki_client

    def as_dict(self):
        wikiId = self.wiki_user.wikiId
        url = f"/wiki/{self._node_id}"
        wiki_link = Link.create(url=url, text=wikiId)
        wiki_url = f"{self.wiki_user.url}{self.wiki_user.scriptPath}"
        wiki_external_link = Link.create(
            url=wiki_url, text=self.wiki_url, target="_blank"
        )

        record = {
            "#": self.row_no,
            "wiki": wiki_link,
            "url": wiki_external_link,
            "version": self.wiki_user.version,
            "pages": "",
            "backup": "✅" if self.wiki_backup.exists() else "❌",
            "git": "✅" if self.wiki_backup.has_git() else "❌",
            "age": "",
            "login": "",
        }
        return record

    def get_software_version_map(
        self, tables: Dict[str, List[Dict[str, Any]]]
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Extract software map from the Special:Version tables.

        Args:
            tables (Dict[str, List[Dict[str, Any]]]): Dictionary of tables with their headers as keys.

        Returns:
            Optional[Dict[str, Dict[str, Any]]]: A dictionary mapping software names to their details,
                                                or None if the "Installed software" table is not found.
        """
        if "Installed software" in tables:
            software = tables["Installed software"]
            software_map, _dup = LOD.getLookup(
                software, "Product", withDuplicates=False
            )
            return software_map
        return None

    def check_version(self) -> str:
        """
        Check the MediaWiki version of the site.

        Returns:
            str: The MediaWiki version string, or an error message if the check fails.
        """
        client = self.wiki_client
        site_info = client.get_site_info()
        generator = site_info.get("generator")
        version = generator.replace("MediaWiki ", "")
        return version

    def check_version_via_url(self) -> str:
        """
        Check the MediaWiki version of the site.

        Returns:
            str: The MediaWiki version string, or an error message if the check fails.
        """
        url = self.wiki_url
        if not "index.php" in self.wiki_url:
            url = f"{url}/index.php"
        version_url = f"{self.wiki_url}?title=Special:Version"
        mw_version = "?"
        try:
            html_tables = HtmlTables(
                version_url, debug=self.debug, showHtml=self.show_html
            )
            tables = html_tables.get_tables("h2")
            software_map = self.get_software_version_map(tables)
            if software_map and "MediaWiki" in software_map:
                mw_version = software_map["MediaWiki"]["Version"]
        except Exception as ex:
            mw_version = f"error: {str(ex)}"
        return mw_version


class Wikis:
    """
    Manages a collection of wiki instances and their states.
    """

    def __init__(self):
        self.wiki_users = WikiUser.getWikiUsers()
        self.wiki_sites = {}
        self.wiki_sites_by_rowno = {}
        self.lod = None

        for wiki_id, wiki_user in self.wiki_users.items():
            wiki_site = WikiSite.ofWikiUser(wiki_user)
            self.wiki_sites[wiki_id] = wiki_site

    def get_wikisite_by_row(self, row_no: int) -> WikiSite:
        """
        Get wiki state by row number.
        """
        return self.wiki_sites_by_rowno.get(row_no)

    def get_lod(self) -> list:
        """
        Get list of dictionaries representation for grid.
        """
        if self.lod is None:
            self.lod = []
            self.wiki_sites_by_rowno = {}
            sorted_sites = sorted(
                self.wiki_sites.values(), key=lambda w: w.wiki_user.wikiId
            )
            for index, wiki_site in enumerate(sorted_sites):
                wiki_site.row_no = index + 1
                self.wiki_sites_by_rowno[wiki_site.row_no] = wiki_site
                record = wiki_site.as_dict()
                self.lod.append(record)
        return self.lod

    def get_wiki_count(self) -> int:
        """
        Get total number of wikis.
        """
        return len(self.wiki_sites)

    def add_to_graph(self, graph: MogwaiGraph, with_progress: bool = False):
        """
        Add all wikis to the graph

        Args:
            graph: MogwaiGraph to add nodes to
            with_progress: bool indicating whether to show progress
        """
        items = self.wiki_sites.items()
        iterator = tqdm(items, desc="Adding wikis to graph") if with_progress else items
        for wiki_id, wiki_site in iterator:
            wiki_user = wiki_site.wiki_user
            props = {
                "hostname": wiki_user.url,
                "wikiId": wiki_id,
                "enabled": True,
                "_instance": wiki_site,
            }
            node_id = graph.add_labeled_node(
                "MediaWikiSite", name=wiki_id, properties=props
            )
            wiki_site._node_id = node_id


@lod_storable
class FrontendSite(Site):
    """
    a frontend site - backed by a WikiSite
    """

    wikiId: str = "wiki"
    defaultPage: str = "Main Page"
    enabled: bool = False

    # non persistent field
    wikisite: WikiSite = field(default=False, init=False, repr=False)
