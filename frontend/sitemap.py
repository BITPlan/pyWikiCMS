"""
Created on 2026-11-06

@author: wf

the sitemap of a site: the members of a wiki category with the urls of the site,
see https://github.com/BITPlan/pyWikiCMS/issues/38
"""

from typing import Any, Dict, List
from urllib.parse import quote
from xml.sax.saxutils import escape


class Sitemap:
    """
    render the pages of a wiki category as a sitemap xml
    """

    CATEGORY = "Sitemap"

    def __init__(self, base_url: str):
        """
        Args:
            base_url(str): the public url of the site e.g. https://www.bitplan.com
        """
        self.base_url = base_url

    @classmethod
    def base_url_of(cls, request: Any) -> str:
        """
        get the public url of the site from the request behind a reverse proxy

        Args:
            request(Request): the FastAPI request

        Returns:
            str: scheme and host as the visitor addressed them
        """
        headers = request.headers
        host = headers.get("x-forwarded-host") or headers.get("host", "")
        scheme = headers.get("x-forwarded-proto", "https")
        base_url = f"{scheme.split(',')[0].strip()}://{host.split(',')[0].strip()}"
        return base_url

    @classmethod
    def get_pages(cls, site: Any, category: str = CATEGORY) -> List[Dict[str, Any]]:
        """
        get the pages of the given category

        Args:
            site: the mwclient Site of the backend wiki
            category(str): the name of the category

        Returns:
            list: the page records with title and touched
        """
        result = site.api(
            "query",
            generator="categorymembers",
            gcmtitle=f"Category:{category}",
            gcmtype="page",
            gcmlimit="max",
            prop="info",
        )
        pages = list(result.get("query", {}).get("pages", {}).values())
        return pages

    def as_xml(self, pages: List[Dict[str, Any]]) -> str:
        """
        render the given pages

        Args:
            pages(list): the page records with title and touched

        Returns:
            str: the sitemap xml, pages sorted by title
        """
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for page in sorted(pages, key=lambda p: p["title"]):
            path = quote(page["title"].replace(" ", "_"), safe="/:()")
            loc = escape(f"{self.base_url}/index.php/{path}")
            lines.append(
                f"<url><loc>{loc}</loc><lastmod>{page['touched']}</lastmod></url>"
            )
        lines.append("</urlset>")
        xml = "\n".join(lines) + "\n"
        return xml
