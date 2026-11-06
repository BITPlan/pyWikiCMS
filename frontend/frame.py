"""
Created on 2020-07-27

@author: wf
"""

from typing import Dict, Optional
from xml.sax.saxutils import quoteattr

from bs4 import BeautifulSoup

from frontend.language import VisitLanguage


class HtmlFrame:
    """
    A class to frame html content with a basic HTML document structure.

    Style and script come from the standard MediaWiki pages of the backend wiki,
    MediaWiki:Common.css and MediaWiki:Common.js, included by action=raw, plus the
    CMS/style, CMS/header/<lang> and CMS/footer/<lang> pages of Category:CMS.
    The navigation comes from MediaWiki:Menu, see issue 36.
    The library ships no css or js of its own, see issue 37.

    Attributes:
        frontend: the WikiFrontend instance
        lang (str): Language of the HTML document.
        title (str): Title of the HTML document.
    """

    def __init__(
        self,
        frontend,
        title: str,
        lang: str = "en",
        head=None,
        visit_lang: Optional[str] = None,
        counterparts: Optional[Dict[str, str]] = None,
        canonical: Optional[str] = None,
    ) -> None:
        """
        Initialize HtmlFrame with a specified language and title.

        Args:
            frontend: the WikiFrontend instance
            title (str): Title for the HTML document, used when head has none.
            lang (str, optional): Language of the HTML document. Defaults to "en".
            head (PageHead, optional): the head metadata MediaWiki rendered, see issue 38
            visit_lang (str, optional): the language of the visit which header, footer
                and menu follow; defaults to the page language, see issue 39
            counterparts (dict, optional): language code to page title of the
                page in the other languages, rendered as the language switch
            canonical (str, optional): the public url of the page on the site, it
                replaces a canonical link the wiki rendered with its own host
        """
        self.frontend = frontend
        self.lang = lang
        self.visit_lang = visit_lang if visit_lang else lang
        self.counterparts = counterparts if counterparts else {}
        self.title = title
        self.head = head
        self.canonical = canonical
        if head is not None:
            if head.title:
                self.title = head.title

    def head_tags(self) -> str:
        """
        Get the meta and link tags MediaWiki rendered for the page.

        Returns:
            str: the tags, one per line, empty without a head
        """
        tags = list(self.head.tags) if self.head is not None else []
        if self.canonical:
            tags = [tag for tag in tags if 'rel="canonical"' not in tag]
            tags.append(f'<link rel="canonical" href={quoteattr(self.canonical)}/>')
        html = "\n".join(f"  {tag}" for tag in tags)
        return html

    @staticmethod
    def head_elements(rendered: str) -> str:
        """
        Get the elements a rendered wiki page may contribute to the head,
        without the wrapper, paragraphs and comments of the MediaWiki parser.

        Args:
            rendered (str): the rendered html of a wiki page

        Returns:
            str: the link, meta, script and style tags, one per line
        """
        soup = BeautifulSoup(rendered, "html.parser")
        tags = soup.find_all(["link", "meta", "script", "style"])
        html = "\n".join(f"  {tag}" for tag in tags)
        return html

    def html_dir(self) -> str:
        """
        Get the text direction of the document.

        Returns:
            str: ltr or rtl
        """
        html_dir = self.head.dir if self.head is not None else "ltr"
        return html_dir

    def wiki_base_url(self) -> str:
        """
        Get the base url of the backend wiki including its script path.

        Returns:
            str: the base url, empty if the frontend has no open wiki
        """
        base_url = ""
        wiki = getattr(self.frontend, "wiki", None)
        wiki_user = getattr(wiki, "wikiUser", None)
        if wiki_user is not None:
            base_url = f"{wiki_user.url}{wiki_user.scriptPath}"
        return base_url

    def common_includes(self) -> str:
        """
        Get the link and script tags for MediaWiki:Common.css and MediaWiki:Common.js.

        Returns:
            str: the tags, empty if the frontend has no open wiki
        """
        html = ""
        base_url = self.wiki_base_url()
        if base_url:
            raw = f"{base_url}/index.php?title=MediaWiki:"
            html = (
                f'  <link rel="stylesheet" href="{raw}Common.css&action=raw&ctype=text/css">\n'
                f'  <script src="{raw}Common.js&action=raw&ctype=text/javascript"></script>'
            )
        return html

    def header(self) -> str:
        """
        Generate the header part of the HTML document.

        Returns:
            str: Header part of an HTML document as a string.
        """
        style_key = "CMS/style"
        style_html = self.head_elements(self.frontend.cms_pages.get(style_key, ""))
        common_includes = self.common_includes()
        head_tags = self.head_tags()
        html = f"""<!doctype html>
<html lang="{self.lang}" dir="{self.html_dir()}">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self.title}</title>
{head_tags}
{common_includes}
{style_html}
</head>
<body>
"""
        return html

    def footer(self) -> str:
        """
        Generate the footer part of the HTML document.

        Returns:
            str: Footer part of an HTML document as a string.
        """
        footer_key = f"CMS/footer/{self.visit_lang}"
        footer_html = self.frontend.cms_pages.get(footer_key, "")
        html = f"""{footer_html}
  </body>
</html>
"""
        return html

    def menu_html(self) -> str:
        """
        Render the site navigation of the frontend, see issue 36.

        Returns:
            str: the nav html, empty if the frontend has no menu
        """
        html = self.hamburger_html() + "\n" + self.bar_html()
        return html

    def menu(self):
        """
        the menu of the visit language, falling back to the frontend's default menu
        see issue 39

        Returns:
            Menu: the menu, None if the frontend has none
        """
        menus = getattr(self.frontend, "menus", None) or {}
        menu = menus.get(self.visit_lang, getattr(self.frontend, "menu", None))
        return menu

    def hamburger_html(self) -> str:
        """
        Render the hamburger form of the navigation, left of the logo.

        Returns:
            str: the html, empty if the frontend has no menu
        """
        menu = self.menu()
        html = ""
        if menu is not None:
            html = menu.hamburger_html(f"/{self.frontend.name}")
        return html

    def bar_html(self) -> str:
        """
        Render the bar form of the navigation, right of the logo.

        Returns:
            str: the html, empty if the frontend has no menu
        """
        menu = self.menu()
        html = ""
        if menu is not None:
            html = menu.bar_html(f"/{self.frontend.name}")
        return html

    def switch_html(self) -> str:
        """
        Render the language switch, right of the bar: one link per other
        language in which the page exists, see issue 39

        Returns:
            str: the html, empty without counterparts
        """
        html = VisitLanguage.switch_html(self.counterparts, f"/{self.frontend.name}")
        return html

    def frame(self, content: str) -> str:
        """
        Frame the given HTML content with the header and footer of the document.

        Args:
            content (str): HTML content to be framed within the HTML structure.

        Returns:
            str: Complete HTML document as a string with the provided content framed.
        """
        header_key = f"CMS/header/{self.visit_lang}"
        header_html = self.frontend.cms_pages.get(header_key, "")
        html = f"""{self.header()}
      <div class="container">
      <div class="site-top d-flex align-items-center">
{self.hamburger_html()}
{header_html}
{self.bar_html()}
{self.switch_html()}
      </div>
{content}
      </div><!-- /.container -->
{self.footer()}"""
        return html
