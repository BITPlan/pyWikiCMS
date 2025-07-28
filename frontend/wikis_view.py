"""
Created on 2025-07-28

@author: wf
"""

from mogwai.web.node_view import NodeView
from nicegui import ui


class WikiView(NodeView):
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
