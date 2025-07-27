"""
Created on 2023-10-31

@author: wf
"""
from basemkit.basetest import Basetest
from backend.wikis import Wikis
from mogwai.core.mogwaigraph import MogwaiGraph


class TestWikis(Basetest):
    """
    test the wikis functionality
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def testWikis(self):
        """
        test wikis         """
        wikis = Wikis()
        graph=MogwaiGraph()
        wikis.add_to_graph(graph, with_progress=True)
        lod = wikis.get_lod()
        debug = True
        if debug:
            print(f"found {len(lod)} wikis")
        pass
