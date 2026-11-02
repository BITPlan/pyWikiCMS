"""
Created on 2026-11-02

@author: wf
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from ngwidgets.basetest import Basetest

from frontend.frame import HtmlFrame
from frontend.menu import Menu


@dataclass
class WikiUserStub:
    """
    the part of a WikiUser the frame needs
    """

    url: str = "https://wiki.example.org"
    scriptPath: str = "/w"


@dataclass
class WikiStub:
    """
    the part of a WikiClient the frame needs
    """

    wikiUser: WikiUserStub = field(default_factory=WikiUserStub)


@dataclass
class FrontendStub:
    """
    the part of a WikiFrontend the frame needs
    """

    name: str = "www"
    cms_pages: Dict[str, str] = field(default_factory=dict)
    wiki: Optional[WikiStub] = None
    menu: Optional[Menu] = None


class TestFrame(Basetest):
    """
    test the html frame
    https://github.com/BITPlan/pyWikiCMS/issues/37
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def test_common_includes(self):
        """
        test that style and script come from MediaWiki:Common.css and Common.js
        """
        frontend = FrontendStub(
            wiki=WikiStub(), cms_pages={"CMS/style": "<style></style>"}
        )
        frame = HtmlFrame(frontend, title="t", lang="de")
        html = frame.frame("<p>c</p>")
        if self.debug:
            print(html)
        self.assertIn(
            'href="https://wiki.example.org/w/index.php?title=MediaWiki:Common.css&action=raw&ctype=text/css"',
            html,
        )
        self.assertIn(
            'src="https://wiki.example.org/w/index.php?title=MediaWiki:Common.js&action=raw&ctype=text/javascript"',
            html,
        )
        self.assertIn('<html lang="de" dir="ltr">', html)
        self.assertNotIn("bootstrap", html)
        self.assertNotIn("jquery", html)

    def test_without_wiki(self):
        """
        test that a frontend without an open wiki frames without includes
        """
        frontend = FrontendStub(menu=Menu.from_markup("* Kontakt\n** Kontakt|Kontakt"))
        frame = HtmlFrame(frontend, title="t")
        html = frame.frame("<p>c</p>")
        self.assertNotIn("Common.css", html)
        self.assertIn('<a href="/www/index.php/Kontakt">Kontakt</a>', html)
        self.assertIn("<p>c</p>", html)
