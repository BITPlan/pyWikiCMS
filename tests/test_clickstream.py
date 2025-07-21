"""
Created on 2023-11-06

@author: wf
"""

from datetime import datetime
import os
import unittest

from basemkit.basetest import Basetest
from frontend.clickstream import ClickstreamManager
from rdflib import Graph, Namespace
from rdflib.plugins.sparql import prepareQuery


class TestClickstreams(Basetest):
    """
    test clickstream log reading and RDF export/import
    """

    def setUp(self, debug=False, profile=True):
        """
        Setup for the tests
        """
        Basetest.setUp(self, debug=debug, profile=profile)
        home_directory = os.path.expanduser("~")
        self.root_path = os.path.join(home_directory, ".clickstream")
        self.rdf_format = "ttl"  # turtle/ttl
        iso_date = datetime.now().strftime("%Y-%m-%d")
        self.rdf_file = os.path.join(self.root_path, f"clicks_{iso_date}")
        self.manager = ClickstreamManager(self.root_path)

    @unittest.skipIf(self.inPublicCI(), "Skip in public CI environment")
    def testReadingLogs(self):
        """
        test reading click stream logs
        """
        limit = 20
        self.manager.load_clickstream_logs(limit=limit)
        self.assertEqual(limit, len(self.manager.clickstream_logs))

    @unittest.skipIf(self.inPublicCI(), "Skip in public CI environment")
    def testRDFExportImportQuery(self):
        """
        Test exporting to RDF, re-importing, and querying for most frequent referrers.
        """
        # Assuming the ClickstreamManager class has been extended with export_to_rdf method
        limit = None
        self.manager.load_clickstream_logs(limit=limit)
        rdf_namespace = "http://cms.bitplan.com/clickstream#"
        rdf_file = self.rdf_file

        # Export to RDF
        self.manager.export_to_rdf(
            rdf_file=rdf_file, rdf_format=self.rdf_format, batch_size=10000
        )

        # Reload the RDF graph from the file
        g = self.manager.reload_graph(self.rdf_file, self.rdf_format)

        # Define a SPARQL query to get the most frequent referrers
        # Adjust the namespace to match the rdf_namespace
        q = prepareQuery(
            """
        SELECT ?referrer (COUNT(?referrer) AS ?count)
        WHERE {
            ?cs <http://cms.bitplan.com/clickstream#referrer> ?referrer .
        }
        GROUP BY ?referrer
        ORDER BY DESC(?count)
        """,
            initNs={"": Namespace(rdf_namespace)},
        )

        # Execute the query
        results = g.query(q)

        # Check that there is at least one result
        self.assertTrue(
            len(results) > 0, "No results found. There should be at least one referrer."
        )

        # Process the query results
        referrers_counts = [(str(row[0]), int(row[1])) for row in results]

        # Find the most frequent referrer
        most_frequent_referrer = max(referrers_counts, key=lambda item: item[1])
        print(
            f"Most frequent referrer: {most_frequent_referrer[0]} with {most_frequent_referrer[1]} hits."
        )
