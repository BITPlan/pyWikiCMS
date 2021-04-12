import unittest
import warnings
from frontend.server import Server
from tests.test_wikicms import TestWikiCMS


class TestGenerator(unittest.TestCase):

    def setUp(self):
        self.testWiki = 'orth'
        warnings.simplefilter("ignore", ResourceWarning)
        self.debug = False
        self.server = TestGenerator.initServer()
        import frontend.webserver
        app = frontend.webserver.app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        self.app = app.test_client()

        # make sure tests run in travis
        sites = [self.testWiki]
        frontend.webserver.wcw.enableSites(sites)
        pass

    @staticmethod
    def initServer():
        '''
        initialize the server
        '''
        Server.homePath = "/tmp"
        server = Server()
        server.logo = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Desmond_Llewelyn_01.jpg/330px-Desmond_Llewelyn_01.jpg"
        server.frontendConfigs = [
            {
                'site': 'orth',
                'wikiId': 'orth',
                'template': 'bootstrap.html',
                'defaultPage': 'Frontend'
            }
        ]
        for frontendConfigs in server.frontendConfigs:
            # make sure ini file is available
            wikiId = frontendConfigs["wikiId"]
            TestWikiCMS.getSMW_WikiUser(wikiId)
        server.store()
        server.load()
        return server

    def getHtml(self, path):
        response = self.app.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data is not None)
        html = response.data.decode()
        if self.debug:
            print(html)
        return html

    def testGeneratorPages(self):
        '''Test if the generator routes are assigned correctly'''
        queries = ['/generate', f'/generate/{self.testWiki}', f'/generate/{self.testWiki}/']
        expected = [
            "Error: access to site",
            "Generator",
            "Error: access to site"
        ]
        # self.debug=True
        for i, query in enumerate(queries):
            html = self.getHtml(query)
            ehtml = expected[i]
            print(html)
            self.assertTrue(ehtml, ehtml in html)

    def test_generate_pages(self):
        '''Test if a given request leads to the expected response'''
        request = {
            'listof_Action': ['y'],
            'submit_Action': ['Generate']
        }
        response = self.app.post(f'/generate/{self.testWiki}', data=request)
        self.assertTrue('List of Actions' in str(response.data))


