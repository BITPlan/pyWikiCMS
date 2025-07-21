"""
Created on 09.03.2025

@author: wf
"""

from typing import Any, Dict, List, Optional

from lodstorage.lod import LOD
from ngwidgets.task_runner import TaskRunner
from ngwidgets.widgets import Link
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.wikipush import WikiPush
from wikibot3rd.wikiuser import WikiUser

from backend.family import WikiBackup
from frontend.html_table import HtmlTables


class MediaWikiSite:
    """
    a MediaWikiSite and it's current  state
    """

    def __init__(
        self,
        wiki_user: WikiUser,
        row_index: int = 0,
        debug: bool = False,
        show_html: bool = False,
    ):
        """
        constructor
        """
        self.row_no = row_index + 1
        self.wiki_user = wiki_user
        self.wiki_url = self.wiki_user.url
        self.debug = debug
        self.show_html = show_html
        self.wiki_backup = WikiBackup(wiki_user)
        self._wiki_client = None
        self.task_runner = TaskRunner()

    @property
    def wiki_client(self) -> WikiClient:
        if not self._wiki_client:
            client = WikiClient.ofWikiUser(self.wiki_user)
            if client.needs_login:
                client.login()
            self._wiki_client = client
        return self._wiki_client

    def as_dict(self):
        url = f"{self.wiki_user.url}{self.wiki_user.scriptPath}"
        link = Link.create(url=url, text=self.wiki_user.wikiId, target="_blank")

        record = {
            "#": self.row_no,
            "wiki": link,
            "version": self.wiki_user.version,
            "pages": "",
            "backup": "✅" if self.wiki_backup.exists() else "❌",
            "git": "✅" if self.wiki_backup.hasGit() else "❌",
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
