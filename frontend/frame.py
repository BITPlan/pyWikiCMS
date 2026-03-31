"""
Created on 2020-07-27

@author: wf
"""

from frontend.resource_loader import ResourceLoader


class HtmlFrame:
    """
    A class to frame html content with a basic HTML document structure.

    CSS and JS resources are loaded from:
      1. frontend/resources/css/*.css and frontend/resources/js/*.js (built-in)
      2. ~/.wikicms/css/*.css and ~/.wikicms/js/*.js (user overrides)

    Files with the same name in the user directory override built-in files.
    All files are sorted alphabetically and concatenated.

    Attributes:
        frontend: the WikiFrontend instance
        lang (str): Language of the HTML document.
        title (str): Title of the HTML document.
    """

    # Shared resource loader instance — created once, cached
    _resource_loader: ResourceLoader = None

    @classmethod
    def get_resource_loader(cls) -> ResourceLoader:
        """
        Return the shared ResourceLoader, creating it on first use.

        Returns:
            ResourceLoader: the singleton resource loader
        """
        if cls._resource_loader is None:
            cls._resource_loader = ResourceLoader()
        return cls._resource_loader

    def __init__(self, frontend, title: str, lang: str = "en") -> None:
        """
        Initialize HtmlFrame with a specified language and title.

        Args:
            frontend: the WikiFrontend instance
            title (str): Title for the HTML document.
            lang (str, optional): Language of the HTML document. Defaults to "en".
        """
        self.frontend = frontend
        self.lang = lang
        self.title = title

    def header(self) -> str:
        """
        Generate the header part of the HTML document.

        Includes Bootstrap 3 CSS/JS and any other resources from the
        css/ and js/ resource directories.

        Returns:
            str: Header part of an HTML document as a string.
        """
        style_key = "CMS/style"
        style_html = self.frontend.cms_pages.get(style_key, "")
        loader = self.get_resource_loader()
        css_includes = loader.css()
        js_includes = loader.js()
        html = f"""<!doctype html>
<html lang="{self.lang}">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self.title}</title>
  {css_includes}
  {js_includes}
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
        html = f"""{self.header()}
{header_html}
      <div class="container">
{content}
      </div><!-- /.container -->
{self.footer()}"""
        return html
