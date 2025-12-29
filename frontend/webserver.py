"""
Created on 2020-12-30

@author: wf
"""

import os
import socket

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from ng3.graph_navigator import GraphNavigatorSolution, GraphNavigatorWebserver
from ngwidgets.input_webserver import InputWebSolution
from ngwidgets.login import Login
from ngwidgets.sso_users_solution import SsoSolution
from ngwidgets.webserver import WebserverConfig
from nicegui import Client, app, ui
from starlette.responses import RedirectResponse
from wikibot3rd.sso_users import Sso_Users

from backend.server import Servers
from backend.site import Wikis
from frontend.servers_view import ServersView
from frontend.version import Version
from frontend.wikicms import WikiFrontends
from frontend.wikigrid import WikiGrid


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
            timeout=10.0,
            short_name="wikicms",
        )
        server_config = WebserverConfig.get(config)
        server_config.solution_class = CmsSolution
        return server_config

    def authenticated(self) -> bool:
        """
        check authentication
        """
        allow = self.login.authenticated()
        if self.server:
            allow = allow or self.server.auto_login
        return allow

    def __init__(self):
        """
        constructor
        """
        GraphNavigatorWebserver.__init__(self, config=CmsWebServer.get_config())
        self.servers = Servers.of_config_path()
        self.wiki_frontends = WikiFrontends(self.servers)
        self.users = Sso_Users(self.config.short_name)
        self.login = Login(self, self.users)
        self.hostname = socket.gethostname()
        self.server = self.servers.servers.get(self.hostname)
        if self.server:
            self.server.probe_local()

        @ui.page("/servers")
        async def show_servers(client: Client):
            if not self.authenticated():
                return RedirectResponse("/login")
            return await self.page(client, CmsSolution.show_servers)

        @ui.page("/wikis")
        async def show_wikis(client: Client):
            if not self.authenticated():
                return RedirectResponse("/login")
            return await self.page(client, CmsSolution.show_wikis)

        @ui.page("/wiki/{wiki_name}")
        async def show_wiki(client: Client, wiki_name: str):
            if not self.authenticated():
                return RedirectResponse("/login")
            return await self.page(client, CmsSolution.show_wiki, wiki_name)

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
        sites = [frontend.name for frontend in self.server.frontends.values()]
        sites=self.wiki_frontends.get_sites(self.args,sites)
        self.wiki_frontends.enableSites(sites)
        module_path = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(module_path, "resources", "schema.yaml")
        self.load_schema(yaml_path)
        ServersView.add_to_graph(self.servers, self.graph, with_progress=True)
        self.wikis = Wikis()
        self.wikis.add_to_graph(self.graph, with_progress=True)
        pass


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
        self.wiki_grid = WikiGrid(self, webserver.wikis)
        self.servers = webserver.servers
        self.server = webserver.server
        self.hostname = webserver.hostname
        self.servers_view = ServersView(self, self.servers)

    def configure_menu(self):
        """
        configure my menu
        """
        InputWebSolution.configure_menu(self)
        self.login = self.webserver.login
        self.sso_solution = SsoSolution(webserver=self.webserver)
        self.sso_solution.configure_menu()
        # icons from https://fonts.google.com/icons
        if self.webserver.authenticated():
            self.link_button(name="wikis", icon_name="menu_book", target="/wikis")
            self.link_button(name="servers", icon_name="cloud", target="/servers")

    async def show_login(self):
        """Show login page"""
        await self.login.login(self)

    async def home(self):
        """
        provide the main content page
        """

        def show():
            with self.content_div:
                ui.label(f"Welcome to {self.hostname}")
                if self.server:
                    html_markup = self.server.as_html()
                    ui.html(html_markup)
                pass

        await self.setup_content_div(show)

    async def show_wikis(self):
        def show():
            with self.content_div:
                self.wiki_grid.setup()

        await self.setup_content_div(show)

    async def show_wiki(self, node_id: str):
        await self.show_node("MediaWikiSite", node_id)

    async def show_servers(self):
        await self.show_nodes("Server")
