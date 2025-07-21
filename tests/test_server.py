"""
Created on 2021-01-06

@author: wf
"""

import unittest

from basemkit.basetest import Basetest

from backend.server import Server, Servers


class TestServer(Basetest):
    """
    test the server specifics
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testServer(self):
        """
        test server functions
        """
        server = Server(name="q", hostname="q.bitplan.com")
        server.probe_remote()
        logo = server.getPlatformLogo()
        if self.debug:
            server.log.dump()
            print(f"platform logo is {logo}")
            print(server.platform)
            print(f"{server.hostname}({server.ip})")

        self.assertTrue("Tux" in logo)
        pass

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testServers(self):
        """
        test the servers collection
        """
        servers = Servers.of_config_path()
        self.assertTrue(len(servers.servers) > 0)

        # Probe all servers
        for server_name, server in servers.servers.items():
            if self.debug:
                print(f"probing {server_name}")
            server.probe_remote()

        if self.debug:
            for server_name, server in servers.servers.items():
                print(f"Server: {server_name}")
                for wiki_name, wiki in server.wikis.items():
                    print(
                        f"  Wiki: {wiki_name} - {wiki.database} - {wiki.apache_config}"
                    )
                server.remote.log.dump()

    @unittest.skipIf(Basetest.inPublicCI(), "Skip in public CI environment")
    def testFamily(self):
        """
        test the servers collection
        """
        servers = Servers.of_config_path()
        arche=servers.servers.get("arche")
        arche.probe_wiki_family()


