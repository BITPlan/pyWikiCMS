"""
Created on 2026-11-06

@author: wf
"""

import gzip
from io import BytesIO

import requests
from ngwidgets.basetest import Basetest
from urllib3 import HTTPResponse

from frontend.wikicms import WikiFrontend


class TestProxy(Basetest):
    """
    test the pass through of backend wiki responses e.g. /robots.txt
    https://github.com/BITPlan/pyWikiCMS/issues/38
    """

    def upstream(self, body: bytes) -> requests.Response:
        """
        get a requests response as the wiki answers with a gzip encoded body
        """
        encoded = gzip.compress(body)
        raw = HTTPResponse(
            body=BytesIO(encoded),
            status=200,
            preload_content=False,
            decode_content=False,
        )
        upstream = requests.Response()
        upstream.status_code = 200
        upstream.raw = raw
        upstream.headers.update(
            {
                "Content-Type": "text/plain",
                "Content-Encoding": "gzip",
                "Content-Length": str(len(encoded)),
                "Transfer-Encoding": "chunked",
                "Connection": "keep-alive",
                "ETag": '"46-gzip"',
            }
        )
        raw.headers["Content-Encoding"] = "gzip"
        return upstream

    def test_gzip_upstream(self):
        """
        the decoded body goes out with its own length and without the wire headers
        """
        body = b"User-agent: *\nDisallow:\n\nSitemap: https://www.bitplan.com/sitemap.xml\n"
        response = WikiFrontend.proxy_response(self.upstream(body))
        self.assertEqual(200, response.status_code)
        self.assertEqual(body, response.body)
        self.assertEqual(str(len(body)), response.headers["content-length"])
        self.assertNotIn("content-encoding", response.headers)
        self.assertNotIn("transfer-encoding", response.headers)
        self.assertNotIn("connection", response.headers)
        self.assertEqual("text/plain", response.headers["content-type"])
        self.assertEqual('"46-gzip"', response.headers["etag"])

    def test_error_status(self):
        """
        the status of the wiki is kept, a 404 stays a 404
        """
        upstream = requests.Response()
        upstream.status_code = 404
        upstream._content = b"not found"
        response = WikiFrontend.proxy_response(upstream)
        self.assertEqual(404, response.status_code)
        self.assertEqual(b"not found", response.body)
