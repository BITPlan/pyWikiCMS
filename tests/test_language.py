"""
Created on 2026-11-02

@author: wf
"""

from ngwidgets.basetest import Basetest

from frontend.frame import HtmlFrame
from frontend.htmlfilter import PageContent
from frontend.language import LanguageSet, VisitLanguage
from frontend.menu import Menu
from tests.test_frame import FrontendStub, WikiStub


class TestLanguage(Basetest):
    """
    test the language of a visit: browser default, visitor choice,
    current language known at all times, switch to the LanguageSet counterpart
    https://github.com/BITPlan/pyWikiCMS/issues/39
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.visit = VisitLanguage(languages=["de", "en"], default="de")

    def test_language_set(self):
        """
        test parsing of the LanguageSet and Language templates
        """
        language_set = LanguageSet.from_markup(
            "__NOTOC__{{LanguageSet|master page=Willkommen|language=en}}\n= Welcome ="
        )
        self.assertEqual("Willkommen", language_set.master_page)
        self.assertEqual("en", language_set.language)
        language_set = LanguageSet.from_markup("{{Language|language=de}}")
        self.assertEqual("", language_set.master_page)
        self.assertEqual("de", language_set.language)
        self.assertIsNone(LanguageSet.from_markup("= no set ="))
        self.assertIsNone(LanguageSet.from_markup(None))
        pc = PageContent(
            page_title="Welcome",
            markup="{{LanguageSet|master page=Willkommen|language=en}}",
        )
        self.assertEqual("en", pc.lang)
        self.assertEqual("Willkommen", pc.master_page)

    def test_accepted(self):
        """
        test the browser language against the offered languages
        """
        self.assertEqual("en", self.visit.accepted("en-US,en;q=0.9,de;q=0.8"))
        self.assertEqual("de", self.visit.accepted("fr-CH, de;q=0.7, en;q=0.3"))
        self.assertEqual("en", self.visit.accepted("fr;q=0.9, en;q=0.8, de;q=0.8"))
        self.assertIsNone(self.visit.accepted("fr,it;q=0.5"))
        self.assertIsNone(self.visit.accepted(None))
        self.assertIsNone(self.visit.accepted(""))

    def test_resolve(self):
        """
        test the order: choice, cookie, browser, default
        """
        self.assertEqual("de", self.visit.resolve())
        self.assertEqual("en", self.visit.resolve(accept_language="en"))
        self.assertEqual("de", self.visit.resolve(accept_language="fr"))
        self.assertEqual("en", self.visit.resolve(cookie="en", accept_language="de"))
        self.assertEqual("de", self.visit.resolve(param="de", cookie="en"))
        # an unknown choice or cookie does not count
        self.assertEqual("en", self.visit.resolve(param="xx", cookie="en"))
        self.assertEqual("en", self.visit.resolve(cookie="xx", accept_language="en"))
        self.assertEqual(["en"], self.visit.others("de"))

    def test_switch_html(self):
        """
        test the language switch
        """
        html = VisitLanguage.switch_html({"en": "Welcome 2026"}, "/www")
        self.assertIn('<nav class="menu-lang', html)
        self.assertIn(
            '<a hreflang="en" href="/www/index.php/Welcome_2026?lang=en">EN</a>', html
        )
        self.assertEqual("", VisitLanguage.switch_html({}))

    def test_frame(self):
        """
        test that header, footer and menu follow the visit language while
        html lang stays the page's, and that the switch is rendered
        """
        menus = {
            "de": Menu.from_markup("* Kontakt\n** Kontakt|Kontakt"),
            "en": Menu.from_markup("* Contact\n** Kontakt|Contact"),
        }
        frontend = FrontendStub(
            wiki=WikiStub(),
            cms_pages={
                "CMS/header/de": "<header>de</header>",
                "CMS/header/en": "<header>en</header>",
                "CMS/footer/de": "<footer>de</footer>",
                "CMS/footer/en": "<footer>en</footer>",
            },
            menu=menus["de"],
            menus=menus,
        )
        frame = HtmlFrame(
            frontend,
            title="Willkommen",
            lang="de",
            visit_lang="en",
            counterparts={"en": "Welcome"},
        )
        html = frame.frame("<p>c</p>")
        if self.debug:
            print(html)
        self.assertIn('<html lang="de"', html)
        self.assertIn("<header>en</header>", html)
        self.assertIn("<footer>en</footer>", html)
        self.assertIn(">Contact</a>", html)
        self.assertNotIn(">Kontakt</a>", html)
        self.assertIn('href="/www/index.php/Welcome?lang=en">EN</a>', html)
        # without a visit language the page language rules and there is no switch
        frame = HtmlFrame(frontend, title="Willkommen", lang="de")
        html = frame.frame("<p>c</p>")
        self.assertIn("<header>de</header>", html)
        self.assertIn(">Kontakt</a>", html)
        self.assertNotIn("menu-lang", html)
