"""
Created on 2026-11-02

@author: wf
"""

from ngwidgets.basetest import Basetest

from frontend.frame import HtmlFrame
from frontend.htmlfilter import PageContent, PageHead
from tests.test_frame import FrontendStub, WikiStub


class TestHead(Basetest):
    """
    test the head pass through from the rendered MediaWiki document
    https://github.com/BITPlan/pyWikiCMS/issues/38
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.rendered = """<!DOCTYPE html>
<html class="client-nojs" lang="de" dir="ltr">
<head>
<meta charset="UTF-8">
<title>Willkommen2026 - BITPlan Wiki</title>
<meta name="generator" content="MediaWiki 1.43.8">
<meta name="robots" content="max-image-preview:standard">
<meta name="description" content="Softwarearchitektur Seminare">
<meta name="viewport" content="width=1000">
<meta property="og:title" content="Willkommen2026">
<link rel="stylesheet" href="/load.php?modules=skins.vector&only=styles">
<link rel="canonical" href="https://wiki.example.org/index.php/Willkommen2026">
<link rel="icon" href="/favicon.ico">
<link rel="search" type="application/opensearchdescription+xml" href="/opensearch_desc.php" title="BITPlan Wiki">
<script>var x=1;</script>
</head>
<body>
<h1 id="firstHeading" class="firstHeading">Willkommen2026</h1>
<div class="mw-parser-output"><p>content</p></div>
</body>
</html>"""

    def test_from_html(self):
        """
        test extraction of lang, dir, title, tags and heading
        """
        head = PageHead.from_html(self.rendered, base_url="https://wiki.example.org")
        if self.debug:
            print(head)
        self.assertEqual("de", head.lang)
        self.assertEqual("ltr", head.dir)
        self.assertEqual("Willkommen2026 - BITPlan Wiki", head.title)
        self.assertEqual("Willkommen2026", head.heading)
        tags = "\n".join(head.tags)
        self.assertIn('name="description"', tags)
        self.assertIn('property="og:title"', tags)
        self.assertIn('rel="canonical"', tags)
        self.assertIn('href="https://wiki.example.org/favicon.ico"', tags)
        self.assertIn('rel="search"', tags)
        for dropped in ["charset", "viewport", "stylesheet", "<script"]:
            self.assertNotIn(dropped, tags)
        self.assertEqual(7, len(head.tags))

    def test_page_content_lang(self):
        """
        test that the markup language wins over the rendered html lang
        """
        head = PageHead.from_html(self.rendered)
        pc = PageContent(page_title="Willkommen2026", head=head)
        self.assertEqual("de", pc.lang)
        pc = PageContent(
            page_title="Welcome", markup="{{LanguageSet|master page=X|language=en}}"
        )
        pc.head = PageHead.from_html(self.rendered)
        pc.detect_lang()
        self.assertEqual("en", pc.lang)

    def test_frame(self):
        """
        test that the frame carries the head through
        """
        head = PageHead.from_html(self.rendered, base_url="https://wiki.example.org")
        frontend = FrontendStub(wiki=WikiStub())
        frame = HtmlFrame(frontend, title="ignored", lang=head.lang, head=head)
        html = frame.frame("<p>c</p>")
        if self.debug:
            print(html)
        self.assertIn('<html lang="de" dir="ltr">', html)
        self.assertIn("<title>Willkommen2026 - BITPlan Wiki</title>", html)
        self.assertIn('rel="canonical"', html)
        self.assertEqual(1, html.count('name="viewport"'))
        self.assertEqual(1, html.count("charset"))
