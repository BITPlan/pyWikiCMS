"""
Created on 2026-03-30

@author: wf
"""

from basemkit.basetest import Basetest

from mwstools_backend.server import Servers
from mwstools_backend.site import Site, WikiSite


class TestHtmlFilter(Basetest):
    """
    test MediaWiki HTML filter
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.servers = Servers.of_config_path()

    def testToReveal(self):
        """
        test converting MediaWiki html with ⌘⌘ headings to reveal.js slideshow
        """
        from frontend.htmlfilter import MediaWikiHtmlFilter

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
