'''
Created on 2020-12-30

@author: wf
'''
from flask import Flask, send_file
from frontend.wikicms import Frontend, Frontends
from frontend.family import WikiFamily
from frontend.widgets import Link, Image, MenuItem
from flask import render_template
import os
from wikibot.wikiuser import WikiUser
from flask_httpauth import HTTPBasicAuth

class AppWrap:
    ''' 
    Wrapper for Flask Web Application 
    '''
    
    def __init__(self, host='0.0.0.0', port=8251, debug=False):
        '''
        constructor
        
        Args:
            wikiId(str): id of the wiki to use as a CMS backend
            host(str): flask host
            port(int): the port to use for http connections
            debug(bool): True if debugging should be switched on
        '''
        self.debug = debug
        self.port = port
        self.host = host    
   
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        self.app = Flask(__name__, template_folder=scriptdir + '/../templates')
        # pimp up jinja2
        self.app.jinja_env.globals.update(isinstance=isinstance)
        self.frontends = Frontends()
        self.frontends.load()
        self.enabledSites = ['admin']
        self.auth= HTTPBasicAuth()
        self.baseUrl=""
        
    @staticmethod
    def splitPath(path):
        '''
        split the given path
        Args:
            path(str): the path to split
        Returns:
            str,str: the site of the path an the actual path
        '''
        # https://stackoverflow.com/questions/2136556/in-python-how-do-i-split-a-string-and-keep-the-separators
        parts = path.split(r"/")
        site = ""
        if len(parts) > 0:
            site = parts[0]
        path = ""
        if len(parts) > 1:
            for part in parts[1:]:
                path = path + "/%s" % (part)
        return site, path    
    
    def enableSites(self, sites):
        '''
        enable the sites given in the sites list
        Args:
            sites(list): a list of strings with wikiIds to be enabled
        '''
        if sites is None:
            return
        for site in sites:
            frontend = Frontend(site)
            self.frontends.enable(frontend)
            self.enabledSites.append(site)
            
    def adminMenuList(self,activeItem:str=None):
        '''
        get the list of menu items for the admin menu
        Args:
            activeItem(str): the active  menu item
        Return:
            list: the list of menu items
        '''
        menuList=[
            MenuItem('/','Home'),
            MenuItem('/wikis','Wikis'),
            MenuItem('/family','Family'),
            MenuItem('https://github.com/BITPlan/pyWikiCMS','github')
            ]
        if activeItem is not None:
            for menuItem in menuList:
                if menuItem.title==activeItem:
                    menuItem.active=True
                if menuItem.url.startswith("/"):
                    menuItem.url="%s%s" % (self.baseUrl,menuItem.url)
        return menuList
            
    def admin(self) -> str:
        '''
        render the admin view
        
        Returns:
            str: the html for the admin view
        '''
        menuList=self.adminMenuList("Home")
        html = render_template("tableview.html", title="Frontends", menuList=menuList,dictList=self.frontends.frontendConfigs)
        return html
    
    def wikis(self) -> str:
        '''
        render the wikis table
        
        Returns:
            str: the html code for the table of wikis
        '''
        wikiUsers = WikiUser.getWikiUsers()
        dictList = []
        for wikiUser in wikiUsers.values():
            dictList.append({
                'wikiId': wikiUser.wikiId,
                'url': Link(wikiUser.url,wikiUser.url),
                'scriptPath':wikiUser.scriptPath,
                'version':wikiUser.version
            })
        menuList=self.adminMenuList("Wikis")      
        html = render_template("tableview.html", menuList=menuList,title="Wikis", dictList=dictList)
        return html    
    
    def logo(self, siteName:str) -> str:
        '''
        render the Logo for the given siteName
        
        Args:
            siteName(str): the name of the site e.g. wiki.bitplan.com
        Returns:
            the rendered Logo for the given Site
        '''
        wikiFamily = WikiFamily()
        if not siteName in wikiFamily.family:
            return self.error("Logo Error","invalid siteName %s" % siteName)
        logoFile=wikiFamily.getLogo(siteName)
        if logoFile is None:
            return "no logo for %s" %siteName
        else:
            return send_file(logoFile)
    
    def error(self,title:str,error:str):
        '''
        render the given error with the given title
        
        Args:
            title(str): the title to display
            error(str): the error to display
    
        Returns:
            str: the html code
        '''
        template="bootstrap.html"
        title=title
        content=None
        html=render_template(template, title=title, content=content, error=error)
        return html
    
    def family(self) -> str:
        '''
        show a html representation of the family of wikis on this server (if any)
        
        Returns:
            str: a html table of all wikis in the family
        '''
        dictList = []
        wikiFamily = WikiFamily()
        for siteName in wikiFamily.family:
            localWiki = wikiFamily.family[siteName]
            logoAccess="%s/family/%s/logo" % (self.baseUrl,siteName)
            dictList.append({
                'site': Link(localWiki.url,localWiki.siteName),
                'logo': Image(logoAccess),
                'database': localWiki.database
            })
        menuList=self.adminMenuList("Family")    
        html = render_template("tableview.html", menuList=menuList,title="Wiki Family", dictList=dictList)
        return html
        
    def wrap(self, siteName, path):
        '''
        wrap the given path for the given site
        Args:
            siteName(str): the name of the site to wrap
            path(path): the path to wrap
        '''
        content = None
        template = "index.html"
        title = "Error"
        if not siteName in self.enabledSites:
            error = "access to site '%s' is not enabled you might want to add it via the --sites command line option" % siteName
        else:
            frontend = self.frontends.get(siteName) 
            if frontend.needsProxy(path):
                return frontend.proxy(path)
            else:
                title, content, error = frontend.getContent(path);
                template = frontend.site.template
        return render_template(template, title=title, content=content, error=error)
       
    def run(self):
        '''
        start the flask webserver
        '''
        self.app.run(debug=self.debug, port=self.port, host=self.host)   
        pass
        
