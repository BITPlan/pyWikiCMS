"""
Created on 2020-07-27

@author: wf
"""


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

    def __init__(self, frontend, title: str, lang: str = "en", head=None) -> None:
        """
        Initialize HtmlFrame with a specified language and title.

        Args:
            frontend: the WikiFrontend instance
            title (str): Title for the HTML document, used when head has none.
            lang (str, optional): Language of the HTML document. Defaults to "en".
            head (PageHead, optional): the head metadata MediaWiki rendered, see issue 38
        """
        self.frontend = frontend
        self.lang = lang
        self.title = title
        self.head = head
        if head is not None:
            if head.title:
                self.title = head.title

    def head_tags(self) -> str:
        """
        Get the meta and link tags MediaWiki rendered for the page.

        Returns:
            str: the tags, one per line, empty without a head
        """
        html = ""
        if self.head is not None and self.head.tags:
            html = "\n".join(f"  {tag}" for tag in self.head.tags)
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
        style_html = self.frontend.cms_pages.get(style_key, "")
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
        footer_key = f"CMS/footer/{self.lang}"
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
        menu = getattr(self.frontend, "menu", None)
        html = ""
        if menu is not None:
            prefix = f"/{self.frontend.name}"
            html = menu.as_html(prefix)
        return html

    def frame(self, content: str) -> str:
        """
        Frame the given HTML content with the header and footer of the document.

        Args:
            content (str): HTML content to be framed within the HTML structure.

        Returns:
            str: Complete HTML document as a string with the provided content framed.
        """
        header_key = f"CMS/header/{self.lang}"
        header_html = self.frontend.cms_pages.get(header_key, "")
        menu_html = self.menu_html()
        html = f"""{self.header()}
{menu_html}
{header_html}
      <div class="container">
{content}
      </div><!-- /.container -->
{self.footer()}"""
        return html
