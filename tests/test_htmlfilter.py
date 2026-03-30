"""
Created on 2026-03-30

@author: wf
"""

from basemkit.basetest import Basetest
from frontend.htmlfilter import MediaWikiHtmlFilter


class TestHtmlFilter(Basetest):
    """
    test MediaWiki HTML filter
    """

    def setUp(self, debug=True, profile=True):
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
        pc.apply_filter(mwf)
        if self.debug:
            print(pc.content)
        # original html preserved
        self.assertIn("mw-editsection", pc.html)
        # filtered content has no editsection
        self.assertNotIn("mw-editsection", pc.content)
        self.assertIn("Ankunft", pc.content)
