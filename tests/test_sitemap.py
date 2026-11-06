"""
Created on 2026-11-06

@author: wf
"""

from ngwidgets.basetest import Basetest

from frontend.sitemap import Sitemap


class TestSitemap(Basetest):
    """
    test the sitemap from a wiki category
    https://github.com/BITPlan/pyWikiCMS/issues/38
    """

    def test_as_xml(self):
        """
        test title encoding, sort order and the host of the site
        """
        pages = [
            {"title": "Willkommen2026", "touched": "2026-11-03T06:00:00Z"},
            {
                "title": "Software Architektur (CPSA-F)",
                "touched": "2026-11-02T06:00:00Z",
            },
            {"title": "A&B Düsseldorf", "touched": "2026-11-01T06:00:00Z"},
        ]
        xml = Sitemap("https://www.bitplan.com").as_xml(pages)
        self.assertIn("<urlset", xml)
        self.assertIn(
            "<loc>https://www.bitplan.com/index.php/Software_Architektur_(CPSA-F)</loc>",
            xml,
        )
        self.assertIn("<lastmod>2026-11-03T06:00:00Z</lastmod>", xml)
        self.assertIn("/index.php/A%26B_D%C3%BCsseldorf</loc>", xml)
        self.assertLess(xml.index("A%26B"), xml.index("Willkommen2026"))

    def test_empty_category(self):
        """
        an empty or missing category gives a valid empty sitemap
        """

        class SiteStub:
            """
            answers as the wiki does for a category without members
            """

            def api(self, action, **kwargs):
                self.kwargs = kwargs
                return {"batchcomplete": ""}

        site = SiteStub()
        pages = Sitemap.get_pages(site)
        self.assertEqual([], pages)
        self.assertEqual("Category:Sitemap", site.kwargs["gcmtitle"])
        self.assertTrue(Sitemap("https://x").as_xml(pages).endswith("</urlset>\n"))

    def test_base_url_of(self):
        """
        the public host comes from the proxy headers
        """

        class RequestStub:
            """
            a request carrying headers only
            """

            def __init__(self, headers):
                self.headers = headers

        cases = [
            ({"host": "localhost:8251"}, "https://localhost:8251"),
            (
                {
                    "host": "localhost:8251",
                    "x-forwarded-host": "www.bitplan.com, localhost:8080",
                    "x-forwarded-proto": "https",
                },
                "https://www.bitplan.com",
            ),
        ]
        for headers, expected in cases:
            self.assertEqual(expected, Sitemap.base_url_of(RequestStub(headers)))
