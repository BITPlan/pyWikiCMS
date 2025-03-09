"""
Created on 2020-12-30

@author: wf
"""
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from ngwidgets.input_webserver import InputWebserver, InputWebSolution
from ngwidgets.webserver import WebserverConfig
from ngwidgets.sso_users_solution import SsoSolution
from nicegui import Client, app, ui

from frontend.server import Server
from frontend.version import Version
from frontend.wikigrid import WikiGrid


class CmsWebServer(InputWebserver):
    """
    WebServer class that manages the server

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
        InputWebserver.__init__(self, config=CmsWebServer.get_config())
        self.server = Server()
        self.server.load()
        self.enabledSites = ["admin"]

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
        frontend = self.server.frontends.get(frontend_name, None)
        if frontend is None:
            raise HTTPException(
                status_code=404, detail=f"frontend {frontend_name} is not available"
            )
        response = frontend.get_path_response(f"/{page_path}")
        return response

    def enableSites(self, siteNames):
        """
        enable the sites given in the sites list
        Args:
            siteNames(list): a list of strings with wikiIds to be enabled
        """
        if siteNames is None:
            return
        for siteName in siteNames:
            self.server.enableFrontend(siteName, self)
            self.enabledSites.append(siteName)

    def configure_run(self):
        """
        configure command line specific details
        """
        InputWebserver.configure_run(self)
        self.enableSites(self.args.sites)


class CmsSolution(InputWebSolution):
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
        self.server = webserver.server

    def configure_menu(self):
        """
        configure my menu
        """
        InputWebSolution.configure_menu(self)
        self.sso_solution = SsoSolution(webserver=self.webserver)
        self.sso_solution.configure_menu()

    async def home(self):
        """
        provide the main content page

        """

        def show():
            with self.content_div:
                self.server_html = ui.html(self.server.asHtml())
                self.wiki_grid.setup()

        await self.setup_content_div(show)
