"""
Created on 2020-12-27

@author: wf
"""
import json

from ngwidgets.basetest import Basetest

from frontend.wikicms import Frontend
from tests.test_webserver import TestWebServer


class TestFrontend(Basetest):
    """
    test the frontend
    """

    def setUp(self):
        Basetest.setUp(self)
        self.server = TestWebServer.initServer()
        pass

    def testWikiPage(self):
        """
        test the route to page translation
        """
        frontend = Frontend("cr")
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

        frontend = self.server.enableFrontend(frontend_name)
        self.assertTrue(frontend.needsProxy(url))
        imageResponse = frontend.proxy(url)
        self.assertFalse(imageResponse is None)
        self.assertEqual(200, imageResponse.status_code)
        self.assertEqual(expected_size, len(imageResponse.content))

    def testProxy(self):
        """
        test the proxy handling
        """
        url = "/images/wiki/thumb/6/62/IMG_0736_Shark.png/400px-IMG_0736_Shark.png"
        self.checkProxiedContent("sharks", url, 79499)

    def testIssue18(self):
        """
        https://github.com/BITPlan/pyWikiCMS/issues/18
        image proxying should work #18
        """
        url = "/images/wiki/thumb/4/42/1738-006.jpg/400px-1738-006.jpg"
        self.checkProxiedContent("www", url, 33742)

    def testIssue14(self):
        """
        test Allow to use templates specified in Wiki
        https://github.com/BITPlan/pyWikiCMS/issues/14
        """
        # see e.g. http://wiki.bitplan.com/index.php/Property:Frame
        frontend = self.server.enableFrontend("www")
        pageTitle = "Feedback"
        frame = frontend.getFrame(pageTitle)
        self.assertEqual("Contact", frame)
        pageTitle, html, error = frontend.getContent(pageTitle)
        if self.debug:
            print(html)
        self.assertIsNone(error)
        self.assertEqual("Feedback", pageTitle)
        self.assertTrue("</div" in html)

    def testIssue15(self):
        """
        test Filter "edit" section buttons

        see https://github.com/BITPlan/pyWikiCMS/issues/15

        """
        frontend = self.server.enableFrontend("cr")
        unfiltered = """<span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=...;action=edit&amp;section=T-1" title="Edit section: ">edit</a><span class="mw-editsection-bracket">]</span></span>"""
        filtered = frontend.doFilter(unfiltered, ["editsection"])
        if self.debug:
            print(filtered)
        self.assertFalse("""<span class="mw-editsection">""" in filtered)
        pageTitle, content, error = frontend.getContent("Issue15")
        self.assertEqual("Issue15", pageTitle)
        self.assertIsNone(error)
        if self.debug:
            print(content)
        self.assertFalse("""<span class="mw-editsection">""" in content)

    def testIssue19(self):
        """
        https://github.com/BITPlan/pyWikiCMS/issues/19
        editsection filter should keep other span's untouched #19
        """
        unfiltered = """<span class="mw-editsection">editsection</span><span class='image'>image section</span>"""
        frontend = self.server.enableFrontend("cr")
        filtered = frontend.doFilter(unfiltered, ["editsection"])
        # print(filtered)
        self.assertTrue("""<span class="image">image section</span>""" in str(filtered))

    def testIssue17(self):
        """
        https://github.com/BITPlan/pyWikiCMS/issues/17

        filter <html><body><div class="mw-parser-output">
        """
        frontend = self.server.enableFrontend("cr")
        unfiltered = (
            """<html><body><div class="mw-parser-output">content</div></body></html>"""
        )
        filtered = frontend.doFilter(unfiltered, "mw-parser-output")
        # self.debug=True
        if self.debug:
            print(filtered)
        self.assertFalse("<html>" in filtered)
        self.assertFalse("<body>" in filtered)
        pageTitle, content, error = frontend.getContent("Issue17")
        self.assertIsNone(error)
        self.assertEqual("Issue17", pageTitle)
        if self.debug:
            print(content)

    def testIssue28_video_support(self):
        """
        https://github.com/BITPlan/pyWikiCMS/issues/28
        """
        url = "/videos/HDV_0878.webm"
        expected_size = 2939840
        self.checkProxiedContent("www", url, expected_size)

    def testToReveal(self):
        """
        test reveal handling
        """
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
        frontend = self.server.enableFrontend("www")
        html = frontend.toReveal(wikihtml)
        if self.debug:
            print(html)

    def testFixHtml(self):
        """
        test that hrefs, images src, srcset videos and objects are
        modified from local-absolute urls to ones with "www"
        """
        frontend = self.server.enableFrontend("www")
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
        frontend = self.server.enableFrontend("www")
        frontend.open()
        cms_pages = frontend.get_cms_pages()
        debug = self.debug
        # debug=True
        if debug:
            print(json.dumps(cms_pages, indent=2))
        self.assertTrue("CMS/footer/de" in cms_pages)
