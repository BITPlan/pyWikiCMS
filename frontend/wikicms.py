"""
Created on 2020-07-27

@author: wf
"""

import logging
import re
import traceback

import requests
from fastapi import Response
from fastapi.responses import HTMLResponse
from wikibot3rd.smw import SMWClient
from wikibot3rd.wikiclient import WikiClient

from mwstools_backend.site import FrontendSite
from frontend.frame import HtmlFrame
from frontend.htmlfilter import MediaWikiHtmlFilter, PageContent
from typing import List


class WikiFrontend(MediaWikiHtmlFilter):
    """
    Wiki Content Management System Frontend
    """

    with_login: bool = True

    def __init__(
        self,
        frontend: FrontendSite,
        parser: str = "lxml",
        proxy_prefixes=["/images/", "/videos"],
        debug: bool = False,
        filterKeys=None,
    ):
        """
        Constructor
        Args:
            frontend(FrontendSite): the frontend
            parser(str): the beautiful soup parser to use e.g. html.parser
            proxy_prefixes(list): the list of prefixes that need direct proxy access
            debug: (bool): True if debugging should be on
            filterKeys: (list): a list of keys for filters to be applied e.g. editsection
        """
        super().__init__(
            parser=parser, debug=debug, filterKeys=filterKeys, site_name=frontend.name
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.proxy_prefixes = proxy_prefixes
        self.frontend = frontend
        self.name = self.frontend.name
        self.wiki = None

    def log(self, msg: str):
        """
        log the given message if debugging is true

        Args:
            msg (str): the message to log
        """
        if self.debug:
            print(msg, flush=True)

    @staticmethod
    def extract_site_and_path(path: str):
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

    def open(self):
        """
        open the frontend

        """
        if self.wiki is None:
            self.wiki = WikiClient.ofWikiId(self.frontend.wikiId)
            if WikiFrontend.with_login:
                self.wiki.login()
            self.smwclient = SMWClient(self.wiki.getSite())
            self.cms_pages = self.get_cms_pages()
            self.frontend.enabled = True

    def get_cms_pages(self) -> dict:
        """
        get the Content Management elements for this site
        """
        cms_pages = {}
        ask_query = "[[Category:CMS]]"
        page_records = self.smwclient.query(ask_query, "cms pages")
        for page_title in list(page_records):
            pageContent = self.getContent(page_title)
            if not pageContent.error:
                cms_pages[page_title] = pageContent.html
            else:
                self.logger.warn(pageContent.error)
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

    def checkPath(self, pagePath: str) -> str:
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

    def needsProxy(self, path: str) -> bool:
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

    def getContent(self, pagePath: str) -> PageContent:
        """get the content for the given pagePath
        Args:
            pagePath(str): the pagePath
            whatToFilter(list): list of filter keys
        Returns:
            pageContent(PageContent): the HTML content for the given path wrapped in a PageContent
        """
        pc = PageContent(html=None, content=None, error=None, page_title="?")
        try:
            if pagePath == "/":
                pc.page_title = self.frontend.defaultPage
            else:
                pc.error = self.checkPath(pagePath)
                pc.page_title = self.wikiPage(pagePath)
            if pc.error is None:
                if self.wiki is None:
                    raise Exception(
                        "getContent without wiki - you might want to call open first"
                    )
                pc.html = self.wiki.getHtml(pc.page_title)
                # apply filter keeping original html for reference, result in pc.content
                pc.apply_filter(self)
        except Exception as e:
            pc.error = self.errMsg(e)

        return pc

    def get_frame(self, page_title: str) -> str:
        """
        get the frame property for the given page_title
        """
        frame = None
        markup = self.wiki.get_wiki_markup(page_title)
        # {{#set:frame=reveal}}
        # {{UseFrame|Contact.rythm|
        patterns = [
            r"{{#set:frame=([^}]+)}}",  # {{#set:frame=reveal}}
            r"{{UseFrame\|([^.]+)",  # {{UseFrame|Contact.rythm|
        ]

        for pattern in patterns:
            match = re.search(pattern, markup)
            if match:
                frame = match.group(1)
        return frame

    def get_path_response(self, path: str) -> Response:
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
            pc = self.getContent(path)
            html_frame = HtmlFrame(self, title=pc.page_title)
            if pc.error:
                response = Response(
                    content=f"Page not found: {path}",
                    status_code=404,
                    media_type="text/html",
                )
                self.log(
                    f"error getting {pc.page_title} for {self.name}:<br>{pc.error}"
                )
            else:
                if "<slideshow" in pc.html or "&lt;slideshow" in pc.html:
                    # reveal.js slideshow: convert content to slides, wrap with reveal
                    pc.content = self.toReveal(pc.content)
                    framed_html = self.wrapWithReveal(pc.content)
                else:
                    framed_html = html_frame.frame(pc.content)
                response = HTMLResponse(framed_html)
        return response


class WikiFrontends:
    """
    wiki frontends
    """

    def __init__(self, servers):
        """
        constructor
        """
        self.servers = servers
        self.wiki_frontends = {}

    def get_sites(self, args, sites: List[str]) -> List[str]:
        """
        Parse sites from command line arguments.

        Handles various input formats:
        - Comma-separated string: "site1,site2" -> ["site1", "site2"]
        - Single site: "site1" -> ["site1"]
        - "all" keyword: returns the input sites list unchanged
        - Multiple arguments: ["site1", "site2"] -> ["site1", "site2"]
        - No arguments: returns all

        Args:
            args: Arguments object with a 'sites' attribute (list of strings)
            sites: Default sites list to return when "all" is specified

        Returns:
            List of parsed site names
        """
        parsed_sites: List[str] = []

        if not args.sites:
            parsed_sites = sites
        elif len(args.sites) == 1:
            arg = args.sites[0]
            if "," in arg:
                parsed_sites = arg.split(",")
            elif arg.lower() == "all":
                parsed_sites = sites
            else:
                parsed_sites = args.sites
        else:
            parsed_sites = args.sites

        return parsed_sites

    def enableSites(self, siteNames):
        """
        enable the sites given in the sites list
        Args:
            siteNames(list): a list of strings with wikiIds to be enabled
        """
        if siteNames is None:
            return
        for siteName in siteNames:
            self.get_frontend(siteName)

    def get_frontend(self, name: str) -> WikiFrontend:
        """
        Get WikiFrontend from cache or create new one
        """
        # Check cache first
        if name in self.wiki_frontends:
            cached_frontend = self.wiki_frontends[name]
            return cached_frontend

        # Create new frontend if not cached
        frontend = self.servers.frontends_by_name.get(name)
        if frontend:
            wiki_frontend = WikiFrontend(frontend)
            wiki_frontend.open()
            # Cache it
            self.wiki_frontends[name] = wiki_frontend
            return wiki_frontend
