"""
Created on 2026-03-30

@author: wf
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup, Comment
from basemkit.yamlable import lod_storable

if TYPE_CHECKING:
    from frontend.forms.registry import FormRegistry


@lod_storable
class PageContent:
    """
    Content of a wiki page with original html preserved for reference
    and filtered content for display.
    """

    page_title: str  # the title of the wiki page
    html: str  # original raw html from the wiki
    content: str  # filtered html for display
    error: Exception  # error if any occurred during retrieval or filtering

    def apply_filter(self, mwf: "MediaWikiHtmlFilter"):
        """
        Apply the given filter to the raw html, storing the result in content
        while keeping the original html for reference.

        Args:
            mwf(MediaWikiHtmlFilter): the filter to apply
        """
        self.content = mwf.filter_html(self.html)


class HtmlFilter:
    """
    filter html content
    """

    def __init__(self, parser: str = "lxml", debug: bool = False):
        """
        Constructor
        Args:
            parser(str): the beautiful soup parser to use e.g. html.parser
            debug(bool): True if debugging should be on
        """
        self.parser = parser
        self.debug = debug

    def unwrap(self, soup) -> str:
        """
        unwrap the soup
        """
        html = str(soup)
        html = html.replace("<html><body>", "")
        html = html.replace("</body></html>", "")
        # Remove empty paragraphs
        html = re.sub(r'<p class="mw-empty-elt">\s*</p>', "", html)
        # Replace multiple newline characters with a single newline character
        html = re.sub(r"\n\s*\n", "\n", html)
        return html


class MediaWikiHtmlFilter(HtmlFilter):
    """
    filter mediawiki content
    """

    def __init__(
        self,
        parser: str = "lxml",
        debug: bool = False,
        filterKeys=None,
        site_name: str = "",
        form_registry: Optional["FormRegistry"] = None,
    ):
        """
        Constructor
        Args:
            parser(str): the beautiful soup parser to use e.g. html.parser
            debug(bool): True if debugging should be on
            filterKeys(list): a list of keys for filters to be applied e.g. editsection
            site_name(str): the name of the site e.g. for prefixing image/href paths
            form_registry(FormRegistry): optional singleton registry for form definitions
        """
        super().__init__(parser=parser, debug=debug)
        self.site_name = site_name
        self.form_registry = form_registry
        if filterKeys is None:
            self.filterKeys = ["editsection", "parser-output", "parser-output"]
        else:
            self.filterKeys = filterKeys

    def filter(self, html: str):
        """
        filter the given html
        """
        return self.doFilter(html, self.filterKeys)

    def filter_html(self, html: str) -> str:
        """
        Apply filters directly on the raw HTML string without re-parsing,
        to avoid lxml re-serialization mangling content.
        Detects wikicms-form divs and replaces them with rendered form HTML
        when a form_registry is set.
        """
        if "editsection" in self.filterKeys:
            html = re.sub(
                r'<span class="mw-editsection">.*?</span>\s*</span>',
                "</span>",
                html,
                flags=re.DOTALL,
            )
        if self.form_registry is not None:
            html = self._replace_form_divs(html)
        return html

    def _replace_form_divs(self, html: str) -> str:
        """
        Find all <div class="wikicms-form" data-form-name="..."> elements and
        replace each with the rendered form HTML from the registry.

        Args:
            html(str): raw HTML string

        Returns:
            str: HTML with form divs replaced
        """
        from frontend.forms.renderer import FormRenderer

        renderer = FormRenderer()

        def replace_match(m: re.Match) -> str:
            form_name = m.group(1)
            form_def = self.form_registry.get(form_name)
            if form_def is None:
                return m.group(0)
            return renderer.render(form_def)

        return re.sub(
            r'<div\s+class="wikicms-form"\s+data-form-name="([^"]+)"[^>]*>.*?</div>',
            replace_match,
            html,
            flags=re.DOTALL,
        )

    def doFilter(self, html, filterKeys):
        # https://stackoverflow.com/questions/5598524/can-i-remove-script-tags-with-beautifulsoup
        soup = BeautifulSoup(html, self.parser)
        if "parser-output" in filterKeys:
            parserdiv = soup.find("div", {"class": "mw-parser-output"})
            if parserdiv:
                inner_html = parserdiv.decode_contents()
                # Parse the inner HTML string to create a new BeautifulSoup object
                soup = BeautifulSoup(inner_html, self.parser)
        # https://stackoverflow.com/questions/5041008/how-to-find-elements-by-class
        if "editsection" in filterKeys:
            for s in soup.select("span.mw-editsection"):
                s.extract()
        for comments in soup.findAll(text=lambda text: isinstance(text, Comment)):
            comments.extract()
        return soup

    def fixNode(self, node, attribute, prefix, delim=None):
        """
        fix the given node

        node (BeautifulSoup): the node
        attribute (str): the name of the attribute e.g. "href", "src"
        prefix (str): the prefix to replace e.g. "/", "/images", "/thumbs"
        delim (str): if not None the delimiter for multiple values
        """
        siteprefix = f"/{self.site_name}{prefix}"
        if attribute in node.attrs:
            attrval = node.attrs[attribute]
            if delim is not None:
                vals = attrval.split(delim)
            else:
                vals = [attrval]
                delim = ""
            newvals = []
            for val in vals:
                if val.startswith(prefix):
                    newvals.append(val.replace(prefix, siteprefix, 1))
                else:
                    newvals.append(val)
            if delim is not None:
                node.attrs[attribute] = delim.join(newvals)

    def fix_images_and_videos(self, soup):
        """
        fix image and video entries in the source code
        """
        for img in soup.findAll("img"):
            self.fixNode(img, "src", "/")
            self.fixNode(img, "srcset", "/", ", ")
        for video in soup.findAll("video"):
            for source in video.findAll("source"):
                self.fixNode(source, "src", "/")

    def fixHtml(self, soup):
        """
        fix the HTML in the given soup

        Args:
            soup(BeautifulSoup): the html parser
        """
        self.fix_images_and_videos(soup)
        # fix absolute hrefs
        for a in soup.findAll("a"):
            self.fixNode(a, "href", "/")
        return soup

    def wrapWithReveal(self, html: str):
        """
        wrap html content with reveal.js structure and dependencies
        """
        wrapped_html = f"""<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/reveal.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/theme/white.css">
</head>
<body>
    <div class="reveal">
        <div class="slides">
{html}
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/reveal.js"></script>
    <script>Reveal.initialize({{
    }});</script>
</body>
</html>"""
        return wrapped_html

    def toReveal(self, html: str):
        """
        convert the given html to reveal
        see https://revealjs.com/
        """
        soup = BeautifulSoup(html, "lxml")
        for h2 in soup.findChildren(recursive=True):
            if h2.name == "h2":
                span = h2.next_element
                if span.name == "span":
                    tagid = span.get("id")
                    if tagid.startswith("⌘⌘"):
                        section = soup.new_tag("section")
                        h2.parent.append(section)
                        section.insert(0, h2)
                        tag = h2.next_element
                        while tag is not None and tag.name != "h2":
                            if tag.parent != h2:
                                section.append(tag)
                            tag = tag.next_element
        html = self.unwrap(soup)
        return html
