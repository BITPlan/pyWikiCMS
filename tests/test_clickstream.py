"""
Created on 2023-11-06

@author: wf
"""
import os
from ngwidgets.basetest import Basetest
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
        self.root_path = os.path.join(home_directory, '.clickstream')
        self.rdf_file = os.path.join(self.root_path, 'clickstream_data.ttl')
        self.manager = ClickstreamManager(self.root_path)
        
    def testReadingLogs(self):
        """
        test reading click stream logs
        """
        limit = 20
        self.manager.load_clickstream_logs(limit=limit)
        self.assertEqual(limit,len(self.manager.clickstream_logs))
    
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
        self.manager.export_to_rdf(rdf_file=rdf_file, rdf_namespace=rdf_namespace)

        # Reload the RDF graph from the file
        g = Graph()
        g.parse(rdf_file, format='turtle')

        # Define a SPARQL query to get the most frequent referrers
        # Adjust the namespace to match the rdf_namespace
        q = prepareQuery("""
        SELECT ?referrer (COUNT(?referrer) AS ?count)
        WHERE {
            ?cs <http://cms.bitplan.com/clickstream#referrer> ?referrer .
        }
        GROUP BY ?referrer
        ORDER BY DESC(?count)
        """, initNs={"": Namespace(rdf_namespace)})
    
        # Execute the query
        results = g.query(q)
    
        # Check that there is at least one result
        self.assertTrue(len(results) > 0, "No results found. There should be at least one referrer.")
        
        # Process the query results
        referrers_counts = [(str(row[0]), int(row[1])) for row in results]
    
        # Find the most frequent referrer
        most_frequent_referrer = max(referrers_counts, key=lambda item: item[1])
        print(f"Most frequent referrer: {most_frequent_referrer[0]} with {most_frequent_referrer[1]} hits.")
