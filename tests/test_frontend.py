"""
Created on 2020-12-27

@author: wf
"""
import asyncio
from datetime import datetime
import json
import threading
from typing import Dict, Any
import unittest
import warnings

from backend.server import Server, Servers
from backend.site import FrontendSite, WikiSite
from fastapi.testclient import TestClient
from frontend.cmsmain import CmsMain
from frontend.webserver import CmsWebServer
from frontend.wikicms import WikiFrontend, WikiFrontends
from ngwidgets.basetest import Basetest
from ngwidgets.webserver_test import WebserverTest

from tests.smw_access import SMWAccess


# this is starlette TestClient under the hood
class TestFrontend(WebserverTest):
    """
    test the frontend
    """

    instance = None

    @classmethod
    def tearDownClass(cls):
        if cls.instance:
            cls.instance.tearDown()

    def tearDown(self):
        """
        avoid the default tearDown behavior which e.g. closes the event
        loop - there are follow-up e.g race condition issues which
        we would rather only have to mitigate once
        """
        # call the unit test tear down and profile time
        Basetest.tearDown(self)
        # make sure each test operates with a new client
        if hasattr(self, "client"):
            self.client = None
        pass

    def get_event_loop_info(self)->Dict[str,Any]:
        """
        Get current event loop information to help debugging
        ValueError: The future belongs to a different loop than the one specified as the loop argument

        """
        try:
            loop = asyncio.get_event_loop()
            loop_info = {
                'is_running': loop.is_running(),
                'is_closed': loop.is_closed(),
                'loop_id': id(loop),
                'thread_id': threading.get_ident(),
                'tasks': len(asyncio.all_tasks(loop)) if not loop.is_closed() else 0
            }
        except RuntimeError as e:
            loop_info = {'error': str(e)}
        return loop_info


    def check_server(self, hint: str = None):
        """
        make sure the server is ready
        """
        timestamp = datetime.now().isoformat()
        if hint is None:
            hint = self._testMethodName
        loop_info=self.get_event_loop_info()
        loop_info_str=json.dumps(loop_info, indent=2)
        msg = f"{timestamp} - {hint} Event loop:{loop_info_str}"
        print(msg)
        pass

    def setUp(self, debug=False, profile=True):
        """
        setUp the test environment making sure we reuse the expensive
        nicegui Webserver
        """
        # special settings for public Continuous Integration environment
        # such as github
        if self.inPublicCI():
            # we do not have credentials in public CI
            WikiFrontend.with_login = False
            # work around ValueError: The future belongs to a different loop
            # than the one specified as the loop argument
            # recreate a new server instance for every test - this is
            # less efficient but should be more stable - in the CI the longer
            # runtime is not so critical
            # TestFrontend.instance=None
        if not TestFrontend.instance:
            server_class = CmsWebServer
            cmd_class = CmsMain
            super().setUp(
                server_class=server_class,
                cmd_class=cmd_class,
                debug=debug,
                profile=profile,
            )
            self.server = self.getServer()
            self.servers = Servers()
            # uncomment if you want to test local setup
            # if self.inPublicCI():
            self.servers.servers["test"] = self.server
            self.servers.init()
            # else:
            # self.servers = Servers.of_config_path()
            self.ws.wiki_frontends = WikiFrontends(self.servers)
            sites = list(self.server.frontends.keys())
            self.ws.wiki_frontends.enableSites(sites)
            TestFrontend.instance = self
        else:
            # reuse setup from first instance
            first = TestFrontend.instance
            self.profiler=first.profiler
            self.server = first.server
            self.servers = first.servers
            self.ws = first.ws
            self.server_runner = first.server_runner
            self.client = TestClient(self.ws.app)
            self.debug = first.debug
        self.check_server("setup")

    def get_frontend(self, name: str) -> WikiFrontend:
        frontend = self.ws.wiki_frontends.get_frontend(name)
        return frontend

    def getServer(self):
        """
        initialize the server
        """
        warnings.simplefilter("ignore", ResourceWarning)
        server = Server(name="test", hostname="localhost")
        server.logo = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Desmond_Llewelyn_01.jpg/330px-Desmond_Llewelyn_01.jpg"
        server.wikis = {"wiki.bitplan.com": WikiSite(name="wiki", wikiId="wiki")}
        server.frontends = {
            "cr": FrontendSite(name="cr", wikiId="wiki"),
            "sharks": FrontendSite(name="sharks", wikiId="wiki", defaultPage="Sharks"),
            "www": FrontendSite(name="www", wikiId="wiki", defaultPage="Welcome"),
        }
        for frontend in server.frontends.values():
            # make sure ini file is available
            SMWAccess.getSMW_WikiUser(frontend.wikiId)
        return server

    def testGetFrontend(self):
        """
        test the route to page translation
        """
        self.check_server()
        frontend = self.get_frontend("www")
        self.assertIsNotNone(frontend)
        self.assertEqual("www", frontend.name)
        pass

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testWebServerPaths(self):
        print("\n=== START testWebServerPaths DEBUG ===")
        self.check_server("initial_state")

        frontend = self.get_frontend("www")
        self.check_server("after_get_frontend")

        test_cases = [
            ("/www/Joker", "Joker"),
            ("/", "<title>pyWikiCMS</title>"),
            ("/www/{Illegal}", "invalid char")
        ]

        for i, (query, ehtml) in enumerate(test_cases):
            print(f"\n--- Request {i+1}: {query} ---")
            self.check_server(f"pre_request_{i}")
            try:
                html = self.get_html(query)
                self.check_server(f"post_request_{i}_success")
                self.assertIn(ehtml, html)
            except Exception as e:
                self.check_server(f"post_request_{i}_error: {str(e)}")
                raise

        print("=== END testWebServerPaths DEBUG ===")

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testRevealIssue20(self):
        """
        test Issue 20
        https://github.com/BITPlan/pyWikiCMS/issues/20
        support reveal.js slideshow if frame is "reveal" #20
        """
        self.check_server()
        html = self.get_html("/www/SMWConTalk2015-05")
        if self.debug:
            print(html)
        self.assertTrue("reveal.min.css" in html)
        self.assertTrue("Reveal.initialize({" in html)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testWikiPage(self):
        """
        test the route to page translation
        """
        self.check_server()
        frontend = self.get_frontend("www")
        routes = ["/index.php/File:Link.png"]
        expectedList = ["File:Link.png"]
        for i, route in enumerate(routes):
            pageTitle = frontend.wikiPage(route)
            if self.debug:
                print(pageTitle)
            expected = expectedList[i]
            self.assertEqual(expected, pageTitle)
        pass

    def checkProxiedContent(self, frontend_name: str, url: str, expected_size: int):
        """
        check access of a proxied content at a given frontend and url for an expected size
        """
        self.check_server()
        frontend = self.get_frontend(frontend_name)
        self.assertTrue(frontend.needsProxy(url))
        imageResponse = frontend.proxy(url)
        self.assertFalse(imageResponse is None)
        self.assertEqual(200, imageResponse.status_code)
        self.assertEqual(expected_size, len(imageResponse.content))

    def testProxy(self):
        """
        test the proxy handling
        """
        self.check_server()
        url = "/images/wiki/thumb/6/62/IMG_0736_Shark.png/400px-IMG_0736_Shark.png"
        self.checkProxiedContent("sharks", url, 79499)

    def testIssue18(self):
        """
        https://github.com/BITPlan/pyWikiCMS/issues/18
        image proxying should work #18
        """
        self.check_server()
        url = "/images/wiki/thumb/4/42/1738-006.jpg/400px-1738-006.jpg"
        self.checkProxiedContent("www", url, 33742)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testIssue14(self):
        """
        test Allow to use templates specified in Wiki
        https://github.com/BITPlan/pyWikiCMS/issues/14
        """
        self.check_server()
        # see e.g. http://wiki.bitplan.com/index.php/Property:Frame
        frontend = self.get_frontend("www")
        test_cases = [("SMWConTalk2015-05", "reveal"), ("Feedback", "Contact")]
        debug = self.debug
        # debug=True
        for test_page, expected_frame in test_cases:
            frame = frontend.get_frame(test_page)
            self.assertEqual(expected_frame, frame)
            page_title, html, error = frontend.getContent(test_page)
            if debug:
                print(html)
            self.assertIsNone(error)
            self.assertEqual(page_title, test_page)
            self.assertTrue("</div" in html or "<p>" in html)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testIssue15(self):
        """
        test Filter "edit" section buttons

        see https://github.com/BITPlan/pyWikiCMS/issues/15

        """
        self.check_server()
        frontend = self.get_frontend("www")
        unfiltered = """<span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=...;action=edit&amp;section=T-1" title="Edit section: ">edit</a><span class="mw-editsection-bracket">]</span></span>"""
        filtered = frontend.doFilter(unfiltered, ["editsection"])
        if self.debug:
            print(filtered)
        self.assertFalse("""<span class="mw-editsection">""" in filtered)
        issue_page = "WikiCMS/Issue15"
        pageTitle, content, error = frontend.getContent(issue_page)
        self.assertEqual(issue_page, pageTitle)
        self.assertIsNone(error)
        if self.debug:
            print(content)
        self.assertFalse("""<span class="mw-editsection">""" in content)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testIssue19(self):
        """
        https://github.com/BITPlan/pyWikiCMS/issues/19
        editsection filter should keep other span's untouched #19
        """
        self.check_server()
        unfiltered = """<span class="mw-editsection">editsection</span><span class='image'>image section</span>"""
        frontend = self.get_frontend("www")
        filtered = frontend.doFilter(unfiltered, ["editsection"])
        # print(filtered)
        self.assertTrue("""<span class="image">image section</span>""" in str(filtered))

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testIssue17(self):
        """
        https://github.com/BITPlan/pyWikiCMS/issues/17

        filter <html><body><div class="mw-parser-output">
        """
        self.check_server()
        frontend = self.get_frontend("www")
        unfiltered = (
            """<html><body><div class="mw-parser-output">content</div></body></html>"""
        )
        filtered = frontend.doFilter(unfiltered, "mw-parser-output")
        # self.debug=True
        if self.debug:
            print(filtered)
        self.assertFalse("<html>" in filtered)
        self.assertFalse("<body>" in filtered)
        issue_page = "WikiCMS/Issue17"
        pageTitle, content, error = frontend.getContent(issue_page)
        self.assertIsNone(error)
        self.assertEqual(issue_page, pageTitle)
        if self.debug:
            print(content)

    def testIssue28_video_support(self):
        """
        https://github.com/BITPlan/pyWikiCMS/issues/28
        """
        self.check_server()
        url = "/videos/HDV_0878.webm"
        expected_size = 2939840
        self.checkProxiedContent("www", url, expected_size)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testToReveal(self):
        """
        test reveal handling
        """
        self.check_server()
        wikihtml = """
        <!DOCTYPE html>
        <html>
          <body>
             <div>
        <h2><span id="⌘⌘_Slide1"></span><span class="mw-headline" id=".E2.8C.98.E2.8C.98_Slide1">⌘⌘ Slide1</span><span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=RevealTest&amp;action=edit&amp;section=1" title="Edit section: ⌘⌘ Slide1">edit</a><span class="mw-editsection-bracket">]</span></span></h2>
<p>Content for slide 1
</p>
<h2><span id="⌘⌘_Slide2"></span><span class="mw-headline" id=".E2.8C.98.E2.8C.98_Slide2">⌘⌘ Slide2</span><span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=RevealTest&amp;action=edit&amp;section=2" title="Edit section: ⌘⌘ Slide2">edit</a><span class="mw-editsection-bracket">]</span></span></h2>
<p>Content for slide 2
</p>
                </div>
            </body>
        <html>"""
        frontend = self.get_frontend("www")
        html = frontend.toReveal(wikihtml)
        debug = self.debug
        # debug = True
        if debug:
            print(html)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testFixHtml(self):
        """
        test that hrefs, images src, srcset videos and objects are
        modified from local-absolute urls to ones with "www"
        """
        self.check_server()
        frontend = self.get_frontend("www")
        pageTitle, content, error = frontend.getContent("Welcome")
        if error is not None:
            print(error)
            self.fail(error)
        self.assertEqual(pageTitle, "Welcome")
        if self.debug:
            print(content)

        self.assertFalse("""href="/index.php""" in content)
        self.assertTrue("""href="/www/index.php""" in content)
        self.assertFalse("""src="/images""" in content)
        self.assertTrue("""src="/www/images""" in content)
        self.assertFalse("""srcset="/images""" in content)
        self.assertTrue("""srcset="/www/images""" in content)
        pass

    def test_cms_pages(self):
        """
        test the content management pages
        """
        self.check_server()
        frontend = self.get_frontend("www")
        frontend.open()
        cms_pages = frontend.get_cms_pages()
        debug = self.debug
        # debug=True
        if debug:
            print(json.dumps(cms_pages, indent=2))
        self.assertTrue("CMS/footer/de" in cms_pages)
