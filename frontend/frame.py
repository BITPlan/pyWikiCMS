class HtmlFrame:
    """
    A class to frame html content with a basic HTML document structure.

    Attributes:
        lang (str): Language of the HTML document.
        title (str): Title of the HTML document.
    """

    def __init__(self, frontend,title: str, lang: str = "en") -> None:
        """
        Initialize HtmlFrame with a specified language and title.

        Args:
            title (str): Title for the HTML document.
            lang (str, optional): Language of the HTML document. Defaults to "en".
        """
        self.frontend=frontend
        self.lang = lang
        self.title = title

    def hamburger_menu(self) -> str:
        """
        Generate the HTML, CSS, and JavaScript for a hamburger menu.

        Returns:
            str: Hamburger menu HTML, CSS, and JavaScript.
        """
        menu_html = """
<!-- Hamburger Menu Start -->
<style>
  /* Basic styling */
  .menu { display: none; }
  .hamburger { cursor: pointer; }
  .hamburger:hover { opacity: 0.7; }

  /* Menu items layout */
  .menu ul { list-style-type: none; padding: 0; }
  .menu li { padding: 8px; background-color: #f0f0f0; margin-bottom: 5px; }

  /* Show the menu when .show class is added via JavaScript */
  .show { display: block; }
</style>

<!-- Hamburger Icon -->
<div class="hamburger" onclick="toggleMenu()">☰</div>

<!-- Menu Items -->
<div class="menu" id="mainMenu">
  <ul>
    <li><a href="#home">Home</a></li>
    <li><a href="#about">About</a></li>
    <li><a href="#services">Services</a></li>
    <li><a href="#contact">Contact</a></li>
  </ul>
</div>

<script>
  function toggleMenu() {
    var menu = document.getElementById("mainMenu");
    if (menu.classList.contains("show")) {
      menu.classList.remove("show");
    } else {
      menu.classList.add("show");
    }
  }
</script>
<!-- Hamburger Menu End -->
"""
        return menu_html

    def header(self) -> str:
        """
        Generate the header part of the HTML document.

        Returns:
            str: Header part of an HTML document as a string.
        """
        style_key=f"CMS/style"
        style_html=self.frontend.cms_pages.get(style_key,"")
        html = f"""<!doctype html>
<html lang="{self.lang}">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self.title}</title>
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
        footer_key=f"CMS/footer/{self.lang}"
        footer_html=self.frontend.cms_pages.get(footer_key,"")
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
        header_key=f"CMS/header/{self.lang}"
        header_html=self.frontend.cms_pages.get(header_key,"")
        html = f"""{self.header()}
{self.hamburger_menu()}  
{header_html}
      <div class="container">
{content}
      </div><!-- /.container -->
{self.footer()}"""
        return html
