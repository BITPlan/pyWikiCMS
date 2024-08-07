"""
Created on 2020-07-27

@author: wf
"""
import re
import traceback

import requests
from bs4 import BeautifulSoup, Comment
from fastapi import Response
from fastapi.responses import HTMLResponse
from wikibot3rd.smw import SMWClient
from wikibot3rd.wikiclient import WikiClient

from frontend.frame import HtmlFrame
from frontend.site import Site


class Frontend(object):
    """
    Wiki Content Management System Frontend
    """

    def __init__(
        self,
        site_name: str,
        parser: str = "lxml",
        proxy_prefixes=["/images/", "/videos"],
        debug: bool = False,
        filterKeys=None,
    ):
        """
        Constructor
        Args:
            site_name(str): the name of the site this frontend is for
            parser(str): the beautiful soup parser to use e.g. html.parser
            proxy_prefixes(list): the list of prefixes that need direct proxy access
            debug: (bool): True if debugging should be on
            filterKeys: (list): a list of keys for filters to be applied e.g. editsection
        """
        self.name = site_name
        self.parser = parser
        self.proxy_prefixes = proxy_prefixes
        self.site = Site(site_name)
        self.debug = debug
        self.wiki = None
        if filterKeys is None:
            self.filterKeys = ["editsection", "parser-output", "parser-output"]
        else:
            self.filterKeys = []

    def log(self, msg:str):
        """
        log the given message if debugging is true

        Args:
            msg (str): the message to log
        """
        if self.debug:
            print(msg, flush=True)

    @staticmethod
    def extract_site_and_path(path:str):
        """
        Splits the given path into the site component and the remaining path.

        This static method assumes that the 'site' is the first element of the
        path when split by "/", and the 'path' is the rest of the string after
        the site.

        Parameters:
        path (str): The complete path to split.

        Returns:
        tuple: A tuple where the first element is the site and the second
               element is the subsequent path.
        """
        # Check if the path is empty or does not contain a "/"
        if not path or "/" not in path:
            return "", path

        # Split the path into parts using the "/" as a separator
        parts = path.split("/")

        # The first part is the site, the rest is joined back into a path
        site = parts[0]
        remaining_path = "/" + "/".join(parts[1:])

        return site, remaining_path

    def open(self, ws=None):
        """
        open the frontend

        Args:
             ws: optional Nicegui webserver
        """
        self.ws = ws
        if self.wiki is None:
            self.wiki = WikiClient.ofWikiId(self.site.wikiId)
            self.wiki.login()
            self.smwclient = SMWClient(self.wiki.getSite())
            self.site.open(ws)
            self.cms_pages = self.get_cms_pages()

    def get_cms_pages(self) -> dict:
        """
        get the Content Management elements for this site
        """
        cms_pages = {}
        ask_query = "[[Category:CMS]]"
        page_records = self.smwclient.query(ask_query, "cms pages")
        for page_title in list(page_records):
            page_title, html, error = self.getContent(page_title)
            if not error:
                cms_pages[page_title] = html
        return cms_pages

    def errMsg(self, ex):
        if self.debug:
            msg = "%s\n%s" % (repr(ex), traceback.format_exc())
        else:
            msg = repr(ex)
        return msg

    def wikiPage(self, pagePath: str) -> str:
        """
        Get the wiki page for the given page path.

        Args:
            pagePath (str): The path of the page.

        Returns:
            str: The title of the page.
        """
        if "/index.php/" in pagePath:
            wikipage = pagePath.replace("/index.php/", "")
        elif pagePath.startswith("/"):
            wikipage = pagePath[1:]
        else:
            wikipage = pagePath
        return wikipage

    def checkPath(self, pagePath:str)->str:
        """
        check the given pathPath

        Args:
            pagePath (str): the page Path to check

        Returns:
            str: None or an error message with the illegal chars being used
        """
        error = None
        self.log(pagePath)
        illegalChars = ["{", "}", "<", ">", "[", "]", "|"]
        for illegalChar in illegalChars:
            if illegalChar in pagePath:
                error = "invalid char %s in given pagePath " % (illegalChar)
        return error

    def needsProxy(self, path:str) -> bool:
        """
        Args:
            path (str): the path to check

        Returns:
            bool: True if this path needs to be proxied
        """
        needs_proxy = False
        for prefix in self.proxy_prefixes:
            needs_proxy = needs_proxy or path.startswith(prefix)
        return needs_proxy

    def proxy(self, path: str) -> str:
        """
        Proxy a request.
        See https://stackoverflow.com/a/50231825/1497139

        Args:
            path (str): the path to proxy

        Returns:
            the proxied result as a string
        """
        wikiUser = self.wiki.wikiUser
        url = f"{wikiUser.url}{wikiUser.scriptPath}{path}"

        # Get the response
        response = requests.get(url)

        return response

    def filter(self, html: str) -> str:
        """
        filter the given html
        """
        return self.doFilter(html, self.filterKeys)

    def fixNode(self, node, attribute, prefix, delim=None):
        """
        fix the given node

        node (BeautifulSoup): the node
        attribute (str): the name of the attribute e.g. "href", "src"
        prefix (str): the prefix to replace e.g. "/", "/images", "/thumbs"
        delim (str): if not None the delimiter for multiple values
        """
        siteprefix = f"/{self.site.name}{prefix}"
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

    def unwrap(self, soup) -> str:
        """
        unwrap the soup
        """
        html = str(soup)
        html = html.replace("<html><body>", "")
        html = html.replace("</body></html>", "")
        # Remove  empty paragraphs
        html = re.sub(r'<p class="mw-empty-elt">\s*</p>', "", html)

        # Replace multiple newline characters with a single newline character
        html = re.sub(r"\n\s*\n", "\n", html)
        return html

    def doFilter(self, html, filterKeys):
        # https://stackoverflow.com/questions/5598524/can-i-remove-script-tags-with-beautifulsoup
        soup = BeautifulSoup(html, self.parser)
        if "parser-output" in filterKeys:
            parserdiv = soup.find("div", {"class": "mw-parser-output"})
            if parserdiv:
                soup = parserdiv
                inner_html = parserdiv.decode_contents()
                # Parse the inner HTML string to create a new BeautifulSoup object
                soup = BeautifulSoup(inner_html, self.parser)
                pass
        # https://stackoverflow.com/questions/5041008/how-to-find-elements-by-class
        if "editsection" in filterKeys:
            for s in soup.select("span.mw-editsection"):
                s.extract()
        for comments in soup.findAll(text=lambda text: isinstance(text, Comment)):
            comments.extract()
        return soup

    def getContent(self, pagePath: str):
        """get the content for the given pagePath
        Args:
            pagePath(str): the pagePath
            whatToFilter(list): list of filter keys
        Returns:
            str: the HTML content for the given path
        """
        content = None
        error = None
        pageTitle = "?"
        try:
            if pagePath == "/":
                pageTitle = self.site.defaultPage
            else:
                error = self.checkPath(pagePath)
                pageTitle = self.wikiPage(pagePath)
            if error is None:
                if self.wiki is None:
                    raise Exception(
                        "getContent without wiki - you might want to call open first"
                    )
                content = self.wiki.getHtml(pageTitle)
                soup = self.filter(content)
                soup = self.fixHtml(soup)
                content = self.unwrap(soup)
        except Exception as e:
            error = self.errMsg(e)
        return pageTitle, content, error

    def toReveal(self, html):
        """
        convert the given html to reveal
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

    def get_path_response(self, path: str) -> str:
        """
        get the repsonse for the the given path

        Args:
            path(str): the path to render the content for

        Returns:
            Response: a FastAPI response
        """
        if self.needsProxy(path):
            html_response = self.proxy(path)
            # Create a FastAPI response object
            response = Response(
                content=html_response.content,
                status_code=html_response.status_code,
                headers=dict(html_response.headers),
            )
        else:
            page_title, content, error = self.getContent(path)
            frame = HtmlFrame(self, title=page_title)
            html = content
            if error:
                html = f"error getting {page_title} for {self.name}:<br>{error}"
            else:
                if "<slideshow" in html or "&lt;slideshow" in html:
                    content = self.toReveal(content)
                    html = content
            framed_html = frame.frame(html)
            response = HTMLResponse(framed_html)
        return response
