"""
Created on 2023-10-31

@author: wf
"""

from basemkit.basetest import Basetest
from mogwai.core.mogwaigraph import MogwaiGraph
from mwstools_backend.site import Wikis


class TestWikis(Basetest):
    """
    test the wikis functionality
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def testWikis(self):
        """
        test wiki
        e.g. 91 wikis in 2.16 secs
        """
        wikis = Wikis()
        graph = MogwaiGraph()
        wikis.add_to_graph(graph, with_progress=True)
        lod = wikis.get_lod()
        debug = True
        if debug:
            print(f"found {len(lod)} wikis")
        pass
