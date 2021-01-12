'''
Created on 2020-12-30

@author: wf
'''
from fb4.app import AppWrap
from flask import send_file
from frontend.server import Server
from frontend.family import WikiFamily
from frontend.widgets import Link, Image, MenuItem
from flask import render_template
from wikibot.wikiuser import WikiUser
import os

class WikiCMSWeb(AppWrap):
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
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        template_folder=scriptdir + '/../templates'
        super().__init__(host=host,port=port,debug=debug,template_folder=template_folder)
        self.server = Server()
        self.server.load()
        self.enabledSites = ['admin']
        
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
    
    def enableSites(self, siteNames):
        '''
        enable the sites given in the sites list
        Args:
            siteNames(list): a list of strings with wikiIds to be enabled
        '''
        if siteNames is None:
            return
        for siteName in siteNames:
            self.server.enableFrontend(siteName)
            self.enabledSites.append(siteName)
            
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
            MenuItem('/frontends','Frontends'),
            MenuItem('https://github.com/BITPlan/pyWikiCMS','github')
            ]
        if activeItem is not None:
            for menuItem in menuList:
                if menuItem.title==activeItem:
                    menuItem.active=True
                if menuItem.url.startswith("/"):
                    menuItem.url="%s%s" % (self.baseUrl,menuItem.url)
        return menuList
            
    def frontends(self) -> str:
        '''
        render the frontends view
        
        Returns:
            str: the html for the admin view
        '''
        menuList=self.adminMenuList("Frontends")
        html = render_template("tableview.html", title="Frontends", menuList=menuList,dictList=self.server.frontendConfigs)
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
        wiki=wikiFamily.family[siteName]
        logoFile=wiki.getLogo()
        if logoFile is None:
            return "no logo for %s" %siteName
        else:
            return send_file(logoFile)
    
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
            apacheAvailable=self.server.checkApacheConfiguration(localWiki.siteId,'available')
            apacheEnabled=self.server.checkApacheConfiguration(localWiki.siteId,'enabled')
            dbName=localWiki.database
            dburl=self.server.sqlGetDatabaseUrl(localWiki.database, localWiki.dbUser, localWiki.dbPassword,hostname='localhost')
            dbState=self.server.sqlDatabaseExist(dburl)
            dbStateSymbol=self.server.stateSymbol(dbState)
            backupState=self.server.sqlBackupStateAsHtml(dbName)
            hereState=self.server.stateSymbol(localWiki.ip==self.server.ip)
            dictList.append({
                'site': "%s(%d)" % (Link(localWiki.url,localWiki.siteName),localWiki.statusCode),
                'logo': Image(logoAccess,height=70),
                'database': "%s %s" % (localWiki.database,dbStateSymbol),
                'SQL backup': backupState,
                'ip': "%s%s" % (hereState,localWiki.ip),
                'apache': "%s/%s" % (apacheAvailable,apacheEnabled)
            })
        menuList=self.adminMenuList("Family")    
        html = render_template("welcome.html", server=self.server,menuList=menuList,title="Wiki Family", dictList=dictList)
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
            frontend = self.server.getFrontend(siteName) 
            if frontend.needsProxy(path):
                return frontend.proxy(path)
            else:
                title, content, error = frontend.getContent(path);
                template = frontend.site.template
        return render_template(template, title=title, content=content, error=error)
        
# 
# route of this Web application
#

# construct the web application    
wcw=WikiCMSWeb()
 
# get the app to define routings for
app=wcw.app 

@app.route('/')
def root():
    return wcw.family()

@app.route('/family')
def family():
    return wcw.family()

@app.route('/frontends')
def frontends():
    return wcw.frontends()

@app.route('/wikis')
def wikis():
    return wcw.wikis()

@app.route('/family/<string:siteName>/logo')
def wikiLogo(siteName:str):
    '''
    render the Logo for the given siteName
    
    Args:
        siteName(str): the name of the site e.g. wiki.bitplan.com
    Returns:
        the rendered Logo for the given Site
    '''
    return wcw.logo(siteName)

@app.route('/<path:path>')
def wrap(path):
    '''
    wrap the url request for the given path
    
    Args:
        path(str): the path to wrap - the path should start with /<wikiId>/ followed by the actual path in the wiki
    '''
    site,path=AppWrap.splitPath(path)
    return wcw.wrap(site,path)

if __name__ == '__main__':
    parser=wcw.getParser(description="Wiki Content Management webservice")
    parser.add_argument('--sites',nargs='+',required=False,help="the sites to enable")
    args=parser.parse_args()
    wcw.optionalDebug(args)
    wcw.enableSites(args.sites)
    wcw.run(args)