"""
Created on 2025-07-23

@author: wf
"""

from mogwai.core.mogwaigraph import MogwaiGraph
from mogwai.web.node_view import NodeView
from nicegui import ui
from tqdm import tqdm

from backend.server import Servers


class ServersView:
    """
    Display servers
    """

    def __init__(self, solution, servers: Servers):
        self.solution = solution
        self.servers = servers

    @classmethod
    def add_to_graph(cls, servers, graph: MogwaiGraph, with_progress: bool):
        """
        add my serves to the graph
        """
        items = servers.servers.items()
        iterator = (
            tqdm(items, desc="Adding servers to graph") if with_progress else items
        )
        for name, server in iterator:
            props = {
                "hostname": server.hostname,
                "platform": server.platform,
                "_instance": server,
            }
            _node = graph.add_labeled_node("Server", name=name, properties=props)
        return graph


class ServerView(NodeView):
    """
    A class responsible for displaying details of a  Server
    """

    def setup_ui(self):
        """Setup UI with code display."""
        try:
            if self.node_data:
                self.server = self.node_data.get("_instance")
                html_markup = self.server.as_html()
                self.html = ui.html(html_markup)
                pass
                # Add probe button
                ui.button("Probe Remote", on_click=self.probe)
            super().setup_ui()
        except Exception as ex:
            self.solution.handle_exception(ex)

    async def probe(self):
        """Probe remote server and update display."""
        try:
            self.server.probe_remote()
            html_markup = self.server.as_html()
            self.html.content = html_markup
        except Exception as ex:
            self.solution.handle_exception(ex)
