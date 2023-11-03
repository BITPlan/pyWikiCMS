'''
Created on 2020-12-30

@author: wf
'''
from nicegui import app,ui, Client
from ngwidgets.input_webserver import InputWebserver
from frontend.server import Server
from ngwidgets.webserver import WebserverConfig
from ngwidgets.background import BackgroundTaskHandler
from frontend.version import Version
from frontend.wikigrid import WikiGrid
from ngwidgets.users import Users
from ngwidgets.login import Login
from fastapi.responses import RedirectResponse

class WebServer(InputWebserver):
    """
    WebServer class that manages the server 
    
    """
    @classmethod
    def get_config(cls)->WebserverConfig:
        copy_right="(c)2023 Wolfgang Fahl"
        config=WebserverConfig(copy_right=copy_right,version=Version(),default_port=8252)
        return config

    def __init__(self):
        '''
        constructor
        
        '''
        InputWebserver.__init__(self,config=WebServer.get_config())
        users=Users("~/.wikicms/")
        self.login=Login(self,users)
        self.server = Server()
        self.server.load()
        self.enabledSites = ['admin']
        self.wiki_grid=WikiGrid(self)
        
        @ui.page('/')
        async def home(client: Client):
            return await self.home(client)
        
        @ui.page('/settings')
        async def settings():
            return await self.settings()
        
        @ui.page('/login')
        async def login(client:Client):    
            return await self.login(client)
        
        @ui.page('/wikis')
        async def wikis(client:Client): 
            if not self.login.authenticated():
                return RedirectResponse('/login')
            return await self.wikis()
     
    @staticmethod
    def extract_site_and_path(path):
        """
        Splits the given path into the site component and the remaining path.

        This static method assumes that the 'site' is the first element of the
        path when split by "/", and the 'path' is the rest of the string after
        the site.

        Parameters:
        path (str): The complete path to split.

        Returns:
        tuple: A tuple where the first element is the site and the second
               element is the subsequent path.
        """
        # Check if the path is empty or does not contain a "/"
        if not path or "/" not in path:
            return "", path

        # Split the path into parts using the "/" as a separator
        parts = path.split("/")

        # The first part is the site, the rest is joined back into a path
        site = parts[0]
        remaining_path = "/".join(parts[1:])

        return site, remaining_path
          
    def enableSites(self, siteNames):
        '''
        enable the sites given in the sites list
        Args:
            siteNames(list): a list of strings with wikiIds to be enabled
        '''
        if siteNames is None:
            return
        for siteName in siteNames:
            self.server.enableFrontend(siteName,self)
            self.enabledSites.append(siteName)
  
    async def home(self, _client:Client):
        """
        Generates the home page with a pdf view
        """
        self.setup_menu()
        with ui.element("div").classes("w-full h-full"):
            self.server_html=ui.html(self.server.asHtml())
            self.wiki_grid.setup()
        await self.setup_footer()
                     
    def configure_menu(self):
        """
        configure specific menu entries
        """
        username=app.storage.user.get('username', '?')
        ui.label(username)
        
    def configure_run(self):
        self.enableSites(self.args.sites)
        self.args.storage_secret=self.server.storage_secret