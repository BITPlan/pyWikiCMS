"""
Created on 2026-03-30

@author: wf
"""

from basemkit.basetest import Basetest
from bs4 import BeautifulSoup

from frontend.htmlfilter import MediaWikiHtmlFilter


class TestHtmlFilter(Basetest):
    """
    test MediaWiki HTML filter
    2 tests in 0.07 secs
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def testToReveal(self):
        """
        test converting MediaWiki html with ⌘⌘ headings to reveal.js slideshow
        """

        html = """<div class="mw-parser-output">
<h2><span id=".E2.8C.98.E2.8C.98_Slide1"></span><span class="mw-headline" id="⌘⌘_Slide1">⌘⌘ Slide1</span></h2>
<p>Content for slide 1</p>
<h2><span id=".E2.8C.98.E2.8C.98_Slide2"></span><span class="mw-headline" id="⌘⌘_Slide2">⌘⌘ Slide2</span></h2>
<p>Content for slide 2</p>
</div>"""
        mwf = MediaWikiHtmlFilter()
        reveal_html = mwf.toReveal(html)
        framed = mwf.wrapWithReveal(reveal_html)
        if self.debug:
            print(framed)
        self.assertIn("reveal.min.css", framed)
        self.assertIn("Reveal.initialize({", framed)

    def testRevealIssue20_slideshow_bundle(self):
        """
        test a page as MediaWiki 1.43 with S5SlideShow renders it: the
        slideshow-bundle box, a table of contents and slides on h2 and h3
        https://github.com/BITPlan/pyWikiCMS/issues/20
        """
        html = """<div class="mw-parser-output">
<div id="slideshow-bundle"><script type="text/javascript">var wgSlideViewFont = "x";</script>
<div class="floatright"><a href="/index.php?title=Talk&amp;action=slide">Slide Show</a></div>
<div class="mw-parser-output"><dl><dt>Title</dt><dd>Graph Approaches</dd>
<dt>Author</dt><dd><a href="/index.php/WF">WF</a></dd><dt>Footer</dt><dd>SimpleGraph</dd></dl></div></div>
<div class="toc" id="toc"><h2 id="mw-toc-heading">Contents</h2><ul><li><a href="#⌘⌘_Slide1">⌘⌘ Slide1</a></li></ul></div>
<h3><span id=".E2.8C.98.E2.8C.98_Slide1"></span><span class="mw-headline" id="⌘⌘_Slide1">⌘⌘ Slide1</span></h3>
<p>Content for slide 1</p>
<h2><span id=".E2.8C.98.E2.8C.98_Slide2"></span><span class="mw-headline" id="⌘⌘_Slide2">⌘⌘ Slide2</span></h2>
<p>Content for slide 2</p>
<h3><span class="mw-headline" id="Detail">Detail</span></h3>
<p>Detail of slide 2</p>
</div>"""
        mwf = MediaWikiHtmlFilter()
        self.assertTrue(mwf.is_slideshow(html))
        self.assertFalse(mwf.is_slideshow("<p>no slides</p>"))
        reveal_html = mwf.toReveal(html)
        if self.debug:
            print(reveal_html)
        soup = BeautifulSoup(reveal_html, "lxml")
        sections = soup.find_all("section")
        # title slide and two slides, the heading without mark stays in slide 2
        self.assertEqual(3, len(sections))
        self.assertEqual("Graph Approaches", sections[0].find("h1").get_text())
        self.assertIn("SimpleGraph", sections[0].get_text())
        self.assertEqual("Slide1", sections[1].find("h3").get_text())
        self.assertIn("Content for slide 1", sections[1].get_text())
        self.assertNotIn("Content for slide 2", sections[1].get_text())
        self.assertEqual("Slide2", sections[2].find("h2").get_text())
        self.assertIn("Detail of slide 2", sections[2].get_text())
        for gone in ["Contents", "wgSlideViewFont", "action=slide"]:
            self.assertNotIn(gone, reveal_html)
        # the mark stays in the anchor ids only
        self.assertNotIn("⌘⌘", soup.get_text())

    def testIssue32_editsection_filter(self):
        """
        test that mw-editsection spans are filtered from frontend output
        https://github.com/BITPlan/pyWikiCMS/issues/32
        """
        from frontend.htmlfilter import PageContent

        raw_html = """<div class="mw-parser-output">
<h2><span class="mw-headline" id="Ankunft">Ankunft</span><span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a href="/index.php?title=Ion2017-02-04&amp;veaction=edit&amp;section=18" class="mw-editsection-visualeditor" title="Edit section: Ankunft">edit</a><span class="mw-editsection-divider"> | </span><a href="/index.php?title=Ion2017-02-04&amp;action=edit&amp;section=18" title="Edit section: Ankunft">edit source</a><span class="mw-editsection-bracket">]</span></span></h2>
<p>Some content</p>
</div>"""
        pc = PageContent(
            page_title="Ion2017-02-04", html=raw_html, content=None, error=None
        )
        mwf = MediaWikiHtmlFilter()
        mwf.filter_page_content(pc)
        if self.debug:
            print(pc.content)
        # original html preserved
        self.assertIn("mw-editsection", pc.html)
        # filtered content has no editsection
        self.assertNotIn("mw-editsection", pc.content)
        self.assertIn("Ankunft", pc.content)
