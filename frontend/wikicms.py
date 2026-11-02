"""
Created on 2020-07-27

@author: wf
"""

import logging
import re
import traceback
from typing import List, Optional

import requests
from fastapi import Response
from fastapi.responses import HTMLResponse
from mwstools_backend.site import FrontendSite
from wikibot3rd.smw import SMWClient
from wikibot3rd.wikiclient import WikiClient

from frontend.frame import HtmlFrame
from frontend.htmlfilter import MediaWikiHtmlFilter, PageContent, PageHead
from frontend.language import VisitLanguage
from frontend.menu import Menu


class WikiFrontend(MediaWikiHtmlFilter):
    """
    Wiki Content Management System Frontend
    """

    with_login: bool = True

    def __init__(
        self,
        frontend: FrontendSite,
        parser: str = "lxml",
        proxy_prefixes=["/images/", "/videos", "/robots.txt", "/sitemap"],
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
            self.visit_language = self.get_visit_language()
            self.menus = {}
            for language in self.visit_language.languages:
                self.menus[language] = self.get_menu(language)
            self.menu = self.menus[self.visit_language.default]
            self.frontend.enabled = True

    def get_visit_language(self) -> VisitLanguage:
        """
        get the languages the site offers from the LanguageSet data of the wiki
        see https://github.com/BITPlan/pyWikiCMS/issues/39

        Returns:
            VisitLanguage: the languages in order of first appearance and the
            default, which is the language of the default page, else the first
        """
        languages = []
        default = None
        ask_query = "[[Master page::+]]|?Language code=language|limit=1000"
        try:
            records = self.smwclient.query(ask_query, "languages")
        except Exception as ex:
            self.logger.warning(f"languages: {self.errMsg(ex)}")
            records = {}
        for page_title, record in records.items():
            language = record.get("language")
            if isinstance(language, list):
                language = language[0] if language else None
            if language:
                if language not in languages:
                    languages.append(language)
                if page_title == self.frontend.defaultPage:
                    default = language
        if not languages:
            languages = ["en"]
        if default is None:
            default = languages[0]
        visit_language = VisitLanguage(languages=languages, default=default)
        return visit_language

    def get_menu(self, language: Optional[str] = None) -> Menu:
        """
        get the site navigation from MediaWiki:Menu/<language>, falling back to
        MediaWiki:Menu and MediaWiki:Sidebar, the convention of MediaWiki:Sidebar/<language>

        see https://github.com/BITPlan/pyWikiCMS/issues/36 and issue 39

        Args:
            language(str): the language code, None for the plain pages only

        Returns:
            Menu: the parsed menu, empty if no page exists
        """
        markup = None
        page_titles = ["MediaWiki:Menu", "MediaWiki:Sidebar"]
        if language:
            page_titles.insert(0, f"MediaWiki:Menu/{language}")
        for page_title in page_titles:
            try:
                markup = self.wiki.get_wiki_markup(page_title)
            except Exception as ex:
                self.logger.info(f"{page_title}: {ex}")
                markup = None
            if markup:
                break
        menu = Menu.from_markup(markup)
        return menu

    def get_counterparts(self, pc: PageContent) -> dict:
        """
        get the pages of the LanguageSet of the given page in the languages
        other than the page's own; the master page wins over other members
        of the same language
        see https://github.com/BITPlan/pyWikiCMS/issues/39

        Args:
            pc(PageContent): the page

        Returns:
            dict: language code to page title, only for languages with a page
        """
        counterparts = {}
        if pc.master_page:
            ask_query = f"[[Master page::{pc.master_page}]]|?Language code=language|limit=50"
            try:
                records = self.smwclient.query(ask_query, "counterparts")
            except Exception as ex:
                self.logger.warning(f"counterparts {pc.master_page}: {self.errMsg(ex)}")
                records = {}
            for other in self.visit_language.others(pc.lang):
                for page_title, record in records.items():
                    page_language = record.get("language")
                    if isinstance(page_language, list):
                        page_language = page_language[0] if page_language else None
                    if page_language == other and page_title != pc.page_title:
                        if other not in counterparts or page_title == pc.master_page:
                            counterparts[other] = page_title
        return counterparts

    def get_cms_pages(self) -> dict:
        """
        get the Content Management elements for this site
        """
        cms_pages = {}
        ask_query = "[[Category:CMS]]"
        page_records = self.smwclient.query(ask_query, "cms pages")
        for page_title in list(page_records):
            # the fragment MediaWiki renders for the page, not the whole document
            try:
                cms_pages[page_title] = self.wiki.getHtml(page_title)
            except Exception as ex:
                self.logger.warning(f"{page_title}: {self.errMsg(ex)}")
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

    def wiki_base_url(self) -> str:
        """
        get the base url of the backend wiki including its script path

        Returns:
            str: the base url
        """
        wikiUser = self.wiki.wikiUser
        base_url = f"{wikiUser.url}{wikiUser.scriptPath}"
        return base_url

    def get_rendered(self, page_title: str) -> Optional[str]:
        """
        get the document MediaWiki renders for the given page, head included
        see https://github.com/BITPlan/pyWikiCMS/issues/38

        Args:
            page_title(str): the title of the page

        Returns:
            str: the rendered document, None if the wiki does not answer 200
        """
        rendered = None
        url = f"{self.wiki_base_url()}/index.php"
        try:
            response = requests.get(url, params={"title": page_title}, timeout=30)
            if response.status_code == 200:
                rendered = response.text
            else:
                self.logger.info(f"{url} {page_title}: {response.status_code}")
        except requests.RequestException as ex:
            self.logger.info(f"{url} {page_title}: {ex}")
        return rendered

    def getContent(self, pagePath: str) -> PageContent:
        """get the content for the given pagePath
        Args:
            pagePath(str): the pagePath
            whatToFilter(list): list of filter keys
        Returns:
            pageContent(PageContent): the HTML content for the given path wrapped in a PageContent
        """
        pc = PageContent()
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
                rendered = self.get_rendered(pc.page_title)
                if rendered:
                    pc.html = rendered
                    pc.head = PageHead.from_html(rendered, self.wiki_base_url())
                else:
                    pc.html = self.wiki.getHtml(pc.page_title)
                pc.markup = self.wiki.get_wiki_markup(pc.page_title)
                pc.detect_lang()
                self.filter_page_content(pc)
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

    def get_path_response(self, path: str, request=None) -> Response:
        """
        get the repsonse for the the given path

        Args:
            path(str): the path to render the content for
            request(Request): the FastAPI request carrying the language of the visit
                as lang parameter, lang cookie or Accept-Language header, see issue 39

        Returns:
            Response: a FastAPI response
        """
        param = cookie = accept_language = None
        if request is not None:
            param = request.query_params.get(VisitLanguage.PARAM)
            cookie = request.cookies.get(VisitLanguage.COOKIE)
            accept_language = request.headers.get("accept-language")
        language = self.visit_language.resolve(param, cookie, accept_language)
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
            counterparts = {}
            if pc.error is None:
                counterparts = self.get_counterparts(pc)
            html_frame = HtmlFrame(
                self,
                title=pc.page_title,
                lang=pc.lang,
                head=pc.head,
                visit_lang=language,
                counterparts=counterparts,
            )
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
                if language != cookie:
                    # the choice holds for the visit: a session cookie
                    response.set_cookie(
                        VisitLanguage.COOKIE, language, httponly=True, samesite="lax"
                    )
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
