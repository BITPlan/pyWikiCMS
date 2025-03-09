"""
Created on 09.03.2025

@author: wf
"""
from frontend.html_table import HtmlTables
from lodstorage.lod import LOD
from typing import Dict,  List, Any, Optional

class MediaWikiSite:
    """
    Class to handle MediaWiki site related operations.
    """

    def __init__(self, wiki_url: str,debug:bool=False):
        """
        Initialize a MediaWikiSite instance.

        Args:
            wiki_url (str): The base URL of the MediaWiki site.
        """
        self.wiki_url = wiki_url
        self.debug=debug

    def get_software_version_map(self, tables: Dict[str, List[Dict[str, Any]]]) -> Optional[Dict[str, Dict[str, Any]]]:
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
        if "index.php" in self.wiki_url:
            version_url = f"{self.wiki_url}?title=Special:Version"
        else:
            version_url = f"{self.wiki_url}/Special:Version"
        mw_version = "?"
        try:
            html_tables = HtmlTables(version_url,debug=self.debug,showHtml=self.debug)
            tables = html_tables.get_tables("h2")
            software_map = self.get_software_version_map(tables)
            if software_map and "MediaWiki" in software_map:
                mw_version = software_map["MediaWiki"]["Version"]
        except Exception as ex:
            mw_version = f"error: {str(ex)}"
        return mw_version