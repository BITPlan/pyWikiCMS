"""
Created on 2026-11-02

@author: wf
"""

from ngwidgets.basetest import Basetest

from frontend.menu import Menu


class TestMenu(Basetest):
    """
    test the navigation from MediaWiki:Menu
    https://github.com/BITPlan/pyWikiCMS/issues/36
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.markup = """* Seminar
** Software Architektur (CPSA-F)|Software Architektur (CPSA-F)
** Trainings|Termine
* Kontakt
** Kontakt|Kontakt
* Extern
** https://example.org/|Beispiel
* Leer
"""

    def test_from_markup(self):
        """
        test parsing of sidebar syntax
        """
        menu = Menu.from_markup(self.markup)
        self.assertEqual(4, len(menu.sections))
        seminar = menu.sections[0]
        self.assertEqual("Seminar", seminar.label)
        self.assertEqual(2, len(seminar.entries))
        self.assertEqual("Software Architektur (CPSA-F)", seminar.entries[0].target)
        self.assertEqual("Termine", seminar.entries[1].label)
        self.assertEqual(0, len(menu.sections[3].entries))

    def test_as_html(self):
        """
        test rendering as script free nav
        """
        menu = Menu.from_markup(self.markup)
        html = menu.as_html("/www")
        if self.debug:
            print(html)
        # hamburger first, left of the logo, then the bar right of it
        self.assertTrue(html.startswith('<nav class="menu-hamburger d-md-none'))
        # bar from the medium breakpoint up: terms inline, last section at the right edge
        self.assertIn('<nav class="menu-bar d-none d-md-flex', html)
        self.assertIn("<summary style=", html)
        self.assertIn(">Seminar</summary>", html)
        self.assertIn(
            '<a class="text-nowrap ms-auto" href="https://example.org/">Beispiel</a>',
            html,
        )
        # hamburger below the breakpoint
        self.assertIn('<summary aria-label="menu" class="fs-2"', html)
        self.assertIn("<li>Seminar\n", html)
        self.assertEqual(
            2,
            html.count(
                '<a href="/www/index.php/Software_Architektur_(CPSA-F)">Software Architektur (CPSA-F)</a>'
            ),
        )
        self.assertEqual(2, html.count('href="/www/index.php/Kontakt"'))
        self.assertNotIn("<script", html)
        self.assertEqual(2, html.count("<details "))

    def test_empty(self):
        """
        test that an absent page yields an empty nav
        """
        menu = Menu.from_markup(None)
        html = menu.as_html()
        self.assertEqual("\n", html)
