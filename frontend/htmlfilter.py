"""
Created on 2026-03-30

@author: wf
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from basemkit.yamlable import lod_storable
from bs4 import BeautifulSoup, Comment

from frontend.forms.mail import FormPost
from frontend.forms.registry import FormRegistry
from frontend.forms.renderer import FormRenderer
from frontend.language import LanguageSet


@dataclass
class PageHead:
    """
    the head metadata MediaWiki rendered for a page, passed through by the frame
    see https://github.com/BITPlan/pyWikiCMS/issues/38

    the frame keeps charset and viewport of its own; stylesheets and scripts of
    the wiki skin are not passed through
    """

    lang: str = "en"
    dir: str = "ltr"
    title: str = ""
    tags: List[str] = field(default_factory=list)
    heading: str = ""

    # link rel values that describe the page rather than the skin
    link_rels = {
        "canonical",
        "alternate",
        "icon",
        "shortcut",
        "apple-touch-icon",
        "search",
        "license",
    }
    # meta names the frame sets itself
    meta_skip = {"viewport", "ResourceLoaderDynamicStyles"}

    @classmethod
    def from_html(
        cls, html: str, base_url: str = "", parser: str = "lxml"
    ) -> "PageHead":
        """
        extract the head metadata from a rendered MediaWiki document

        Args:
            html(str): the rendered document
            base_url(str): the base url of the wiki to make relative link hrefs absolute
            parser(str): the beautiful soup parser to use

        Returns:
            PageHead: the extracted head
        """
        head = cls()
        soup = BeautifulSoup(html, parser)
        html_tag = soup.find("html")
        if html_tag is not None:
            head.lang = html_tag.get("lang", head.lang)
            head.dir = html_tag.get("dir", head.dir)
        title_tag = soup.find("title")
        if title_tag is not None:
            head.title = title_tag.get_text().strip()
        if soup.head is not None:
            for tag in soup.head.find_all(["meta", "link"]):
                if tag.name == "meta":
                    keep = "charset" not in tag.attrs and (
                        tag.get("name", "") not in cls.meta_skip
                    )
                else:
                    rels = set(tag.get("rel") or [])
                    keep = bool(rels & cls.link_rels)
                    href = tag.get("href", "")
                    if keep and href.startswith("/") and base_url:
                        tag["href"] = f"{base_url}{href}"
                if keep:
                    head.tags.append(str(tag))
        heading = soup.find(id="firstHeading")
        if heading is not None:
            head.heading = heading.get_text().strip()
        return head


@lod_storable
class PageContent:
    """
    Content of a wiki page with original html preserved for reference
    and filtered content for display.
    """

    page_title: str = "?"  # the title of the wiki page
    markup: str = None  # original wiki markup from the wiki
    html: str = None  # original raw html from the wiki
    content: str = None  # filtered html for display
    error: Exception = None  # error if any occurred during retrieval or filtering
    lang: str = (
        "en"  # the language of the wiki page - potentially derived from it's markup
    )
    master_page: str = (
        ""  # the master page of the LanguageSet of the page, see issue 39
    )
    head: Optional[PageHead] = None  # head metadata of the rendered document
    form_post: Optional[FormPost] = None  # the submitted form state, see issue 41

    def __post_init__(self):
        self.detect_lang()

    def detect_lang(self):
        """
        detect the language: the Language or LanguageSet template of the markup wins,
        then the html lang of the rendered document
        """
        language_set = LanguageSet.from_markup(self.markup)
        if language_set is not None:
            self.master_page = language_set.master_page
            if language_set.language:
                self.lang = language_set.language
                return
        if self.head is not None and self.head.lang:
            self.lang = self.head.lang


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
        self.wiki_url = ""  # absolute base url of the backend wiki, see issue 44
        self.form_registry = FormRegistry.instance()
        if filterKeys is None:
            self.filterKeys = ["editsection", "parser-output", "parser-output"]
        else:
            self.filterKeys = filterKeys

    def filter_page_content(self, pc: PageContent):
        """
        filter the given page content
        """
        self.filter(pc)

    def filter(self, pc: PageContent):
        """
        Filter the given page content.

        Pipeline:
        1. doFilter — parse with BeautifulSoup, strip parser-output wrapper,
           editsection spans, and comments.  Returns cleaned soup.
        2. fixHtml — rewrite image/video/link paths for the CMS frontend.
        3. unwrap — convert soup to HTML string, strip lxml wrapper tags.
        4. _replace_form_divs — replace wikicms-form divs with rendered forms.
        5. Store result in pc.content; pc.html stays as the original.

        Args:
            pc(PageContent): the page content to filter

        Returns:
            PageContent: the same object with pc.content set
        """
        soup = self.doFilter(pc.html, self.filterKeys)
        soup = self.fixHtml(soup)
        filtered_html = self.unwrap(soup)
        filtered_html = self._replace_form_divs(filtered_html, pc.lang, pc.form_post)
        pc.content = filtered_html
        return pc

    def _replace_form_divs(
        self, html: str, lang: str = "en", form_post: Optional[FormPost] = None
    ) -> str:
        """
        Find all <div class="wikicms-form" data-form-name="..."> elements and
        replace each with the rendered form HTML from the registry.

        Args:
            html(str): the HTML string to process
            lang(str): language code for i18n resolution
            form_post(FormPost): the submitted state of the form of that name,
                values and errors or the message of a valid submission

        Returns:
            str: the HTML with form divs replaced
        """
        if self.form_registry is None:
            result = html
        else:
            renderer = FormRenderer()

            def replace_match(m: re.Match) -> str:
                form_name = m.group(1)
                form_def = self.form_registry.get(form_name)
                if form_def is None:
                    replacement = m.group(0)
                elif form_post is not None and form_post.name == form_name:
                    replacement = renderer.render(
                        form_def,
                        values=form_post.values,
                        errors=form_post.errors,
                        lang=lang,
                        message=form_post.message,
                    )
                elif form_post is not None and form_post.name == "":
                    # prefill from URL parameters, see issue 44
                    values = form_def.prefill(form_post.values)
                    replacement = renderer.render(form_def, values=values, lang=lang)
                else:
                    replacement = renderer.render(form_def, lang=lang)
                return replacement

            result = re.sub(
                r'<div\s+class="wikicms-form"\s+data-form-name="([^"]+)"[^>]*>.*?</div>',
                replace_match,
                html,
                flags=re.DOTALL,
            )
        return result

    def doFilter(self, html: str, filterKeys) -> BeautifulSoup:
        """
        Parse *html* with BeautifulSoup and apply structural filters.

        Args:
            html(str): the raw HTML string
            filterKeys(list): which filters to apply

        Returns:
            BeautifulSoup: the cleaned soup
        """
        # https://stackoverflow.com/questions/5598524/can-i-remove-script-tags-with-beautifulsoup
        soup = BeautifulSoup(html, self.parser)
        if "parser-output" in filterKeys:
            parserdiv = soup.find("div", {"class": "mw-parser-output"})
            if parserdiv:
                inner_html = parserdiv.decode_contents()
                soup = BeautifulSoup(inner_html, self.parser)
        # https://stackoverflow.com/questions/5041008/how-to-find-elements-by-class
        if "editsection" in filterKeys:
            for s in soup.select("span.mw-editsection"):
                s.extract()
        for comments in soup.find_all(string=lambda text: isinstance(text, Comment)):
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
            self.fix_wiki_link(a)
            self.fixNode(a, "href", "/")
        return soup

    def fix_wiki_link(self, node) -> None:
        """
        a link to the backend wiki by absolute url, as fullurl produces it,
        becomes a root relative link of the site, see issue 44

        Args:
            node: the anchor node
        """
        href = node.attrs.get("href", "")
        if self.wiki_url and href.startswith(self.wiki_url + "/"):
            node.attrs["href"] = href[len(self.wiki_url) :]

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
