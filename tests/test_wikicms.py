"""
Created on 2020-07-27

@author: wf
"""

# from wikibot.smw import SMWClient
from basemkit.basetest import Basetest

from frontend.forms.mail import FormPost
from frontend.wikicms import WikiFrontend
from tests.smw_access import SMWAccess
from tests.test_frame import FrontendStub


class TestWikiCMS(Basetest):
    """
    test the Mediawiki based Content Management System
    2 tests in 0.2 secs
    """

    def setUp(self):
        Basetest.setUp(self)
        pass

    def tearDown(self):
        pass

    def testWikiCMS(self):
        """test CMS access"""
        wikiclient = SMWAccess.getSMW_Wiki("wiki")
        pageTitle = "Main Page"
        page = wikiclient.getPage(pageTitle)
        text = page.text()
        debug = self.debug
        # debug = True
        if debug:
            print(text)
        self.assertTrue("Joker" in text)
        pass

    def test_rendered_params(self):
        """
        the rendered document is fetched with the title and the frontend parameter
        carrying the site name, so the wiki knows it is called from a frontend
        https://github.com/BITPlan/pyWikiCMS/issues/40
        """
        wiki_frontend = WikiFrontend(FrontendStub(name="www"))
        params = wiki_frontend.rendered_params("Willkommen2026")
        self.assertEqual({"title": "Willkommen2026", "frontend": "www"}, params)

    def test_resolve_params(self):
        """
        a title parameter names the page, the other parameters prefill a form
        https://github.com/BITPlan/pyWikiCMS/issues/44
        """
        wiki_frontend = WikiFrontend(FrontendStub(name="www"))
        params = {"title": "Trainingsanmeldung", "training": "UML-Tag", "lang": "de"}
        path, form_post = wiki_frontend.resolve_params("/index.php", params)
        self.assertEqual("/index.php/Trainingsanmeldung", path)
        self.assertEqual("", form_post.name)
        self.assertEqual({"training": "UML-Tag"}, form_post.values)
        path, form_post = wiki_frontend.resolve_params("/Kontaktformular", {})
        self.assertEqual("/Kontaktformular", path)
        self.assertIsNone(form_post)
        submitted = FormPost(name="contact", values={"name": "E"})
        _path, form_post = wiki_frontend.resolve_params(
            "/Kontaktformular", {"name": "X"}, submitted
        )
        self.assertIs(submitted, form_post)

    def test_wiki_page_trailing_slash(self):
        """
        a short URL with a trailing slash names the same page
        https://github.com/BITPlan/pyWikiCMS/issues/43
        """
        wiki_frontend = WikiFrontend(FrontendStub(name="www"))
        for path in ("/Registration/", "/Registration", "/index.php/Registration/"):
            self.assertEqual("Registration", wiki_frontend.wikiPage(path), path)

    def test_extract_site_and_path(self):
        """
        Test splitting the path into site and path.
        """
        # Test paths and their expected results.
        paths = ["admin/", "or/test"]
        expected_results = [("admin", "/"), ("or", "/test")]

        for index, test_path in enumerate(paths):
            # Extract site and path using the Webserver method.
            site, path = WikiFrontend.extract_site_and_path(test_path)

            # If debugging is enabled, print the results.
            if getattr(self, "debug", False):
                print(f"Site: {site}, Path: {path}")

            # Get the expected site and path.
            expected_site, expected_path = expected_results[index]

            # Assert that the results match the expectations.
            self.assertEqual(expected_site, site)
            self.assertEqual(expected_path, path)
