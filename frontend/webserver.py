"""
Created on 2020-12-30

@author: wf
"""

import os

from backend.server import Servers
from basemkit.persistent_log import Log
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from frontend.servers_view import ServersView
from frontend.version import Version
from frontend.wikicms import WikiFrontend, WikiFrontends
from frontend.wikigrid import WikiGrid
from mogwai.core import MogwaiGraph
from mogwai.schema.graph_schema import GraphSchema
from mogwai.web.node_view import NodeTableView, NodeViewConfig
from ng3.graph_navigator import GraphNavigatorSolution, GraphNavigatorWebserver
from ngwidgets.input_webserver import InputWebSolution
from ngwidgets.login import Login
from ngwidgets.sso_users_solution import SsoSolution
from ngwidgets.webserver import WebserverConfig
from nicegui import Client, app, ui
from starlette.responses import RedirectResponse
from wikibot3rd.sso_users import Sso_Users


class CmsWebServer(GraphNavigatorWebserver):
    """
    WebServer class that manages the servers

    """

    @classmethod
    def get_config(cls) -> WebserverConfig:
        copy_right = "(c)2023-2025 Wolfgang Fahl"
        config = WebserverConfig(
            copy_right=copy_right,
            version=Version(),
            default_port=8252,
            short_name="wikicms",
        )
        server_config = WebserverConfig.get(config)
        server_config.solution_class = CmsSolution
        return server_config

    def __init__(self):
        """
        constructor
        """
        GraphNavigatorWebserver.__init__(self, config=CmsWebServer.get_config())
        self.servers = Servers.of_config_path()
        self.wiki_frontends = WikiFrontends(self.servers)
        self.users = Sso_Users(self.config.short_name)
        self.login = Login(self, self.users)

        @ui.page("/servers")
        async def show_solutions(client: Client):
            if not self.login.authenticated():
                return RedirectResponse("/login")
            return await self.page(client, CmsSolution.show_servers)

        @ui.page("/login")
        async def login(client: Client) -> None:
            return await self.page(client, CmsSolution.show_login)

        @app.get("/{frontend_name}/{page_path:path}")
        def render_path(frontend_name: str, page_path: str) -> HTMLResponse:
            """
            Handles a GET request to render the path of the given frontend.

            Args:
                frontend_name: The name of the frontend to be rendered.
                page_path: The specific path within the frontend to be rendered.

            Returns:
                An HTMLResponse containing the rendered page content.

            """
            return self.render_path(frontend_name, page_path)

    def render_path(self, frontend_name: str, page_path: str):
        """
        Renders the content for a specific path of the given frontend.

        Args:
            frontend_name: The name of the frontend to be rendered.
            page_path: The specific path within the frontend to be rendered.

        Returns:
            An HTMLResponse containing the rendered page content or an error page if something goes wrong.

        Raises:
            SomeException: If an error occurs during page content retrieval or rendering.

        """
        wiki_frontend = self.wiki_frontends.wiki_frontends.get(frontend_name, None)
        if wiki_frontend is None:
            raise HTTPException(
                status_code=404, detail=f"frontend {frontend_name} is not available"
            )
        response = wiki_frontend.get_path_response(f"/{page_path}")
        return response

    def configure_run(self):
        """
        configure command line specific details
        """
        super().configure_run()
        self.wiki_frontends.enableSites(self.args.sites)
        module_path = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(module_path, "resources", "schema.yaml")
        self.load_schema(yaml_path)
        ServersView.add_to_graph(self.servers, self.graph, with_progress=True)


class CmsSolution(GraphNavigatorSolution):
    """
    Content management solution
    """

    def __init__(self, webserver: CmsWebServer, client: Client):
        """
        Initialize the solution

        Calls the constructor of the base solution
        Args:
            webserver (Cms    WebServer): The webserver instance associated with this context.
            client (Client): The client instance this context is associated with.
        """
        super().__init__(webserver, client)  # Call to the superclass constructor
        self.wiki_grid = WikiGrid(self)
        self.servers = webserver.servers
        self.servers_view = ServersView(self, self.servers)
        self.server_html = {}

    def configure_menu(self):
        """
        configure my menu
        """
        InputWebSolution.configure_menu(self)
        self.login=self.webserver.login
        self.sso_solution = SsoSolution(webserver=self.webserver)
        self.sso_solution.configure_menu()
        # icons from https://fonts.google.com/icons
        if self.login.authenticated():
            self.link_button(name="servers", icon_name="cloud", target="/servers")

    async def home(self):
        """
        provide the main content page
        """

        def show():
            with self.content_div:
                self.wiki_grid.setup()

        await self.setup_content_div(show)

    async def show_nodes(self, node_type: str):
        """
        show nodes of the given type

        Args:
            node_type(str): the type of nodes to show
        """

        def show():
            try:
                config = NodeViewConfig(
                    solution=self,
                    graph=self.graph,
                    schema=self.schema,
                    node_type=node_type,
                )
                if not config.node_type_config:
                    ui.label(f"invalid_node_type: {node_type}")
                    return
                node_table_view = NodeTableView(config=config)
                node_table_view.setup_ui()
            except Exception as ex:
                self.handle_exception(ex)

        await self.setup_content_div(show)

    async def show_servers(self):
        await self.show_nodes("Server")
