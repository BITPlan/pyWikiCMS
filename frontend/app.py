'''
Created on 2020-12-30

@author: wf
'''
from flask import Flask
from frontend.wikicms import Frontend, Frontends
from frontend.family import LocalWiki
from flask import render_template
import os
from wikibot.wikiuser import WikiUser

class AppWrap:
    ''' 
    Wrapper for Flask Web Application 
    '''
    
    def __init__(self, host='0.0.0.0',port=8251,debug=False):
        '''
        constructor
        
        Args:
            wikiId(str): id of the wiki to use as a CMS backend
            host(str): flask host
            port(int): the port to use for http connections
            debug(bool): True if debugging should be switched on
        '''
        self.debug=debug
        self.port=port
        self.host=host    
        scriptdir=os.path.dirname(os.path.abspath(__file__))
        self.app = Flask(__name__,template_folder=scriptdir+'/../templates')
        self.frontends=Frontends()
        self.frontends.load()
        self.enabledSites=['admin']
        
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
        parts=path.split(r"/")
        site=""
        if len(parts)>0:
            site=parts[0]
        path=""
        if len(parts)>1:
            for part in parts[1:]:
                path=path+"/%s" % (part)
        return site,path    
    
    def enableSites(self,sites):
        '''
        enable the sites given in the sites list
        Args:
            sites(list): a list of strings with wikiIds to be enabled
        '''
        if sites is None:
            return
        for site in sites:
            frontend=Frontend(site)
            self.frontends.enable(frontend)
            self.enabledSites.append(site)
            
    def admin(self)->str:
        '''
        render the admin view
        
        Returns:
            str: the html for the admin view
        '''
        html=render_template("tableview.html",title="Sites",dictList=self.frontends.frontendConfigs)
        return html
    
    def wikis(self)->str:
        '''
        render the wikis table
        
        Returns:
            str: the html code for the table of wikis
        '''
        wikiUsers=WikiUser.getWikiUsers()
        dictList=[]
        for wikiUser in wikiUsers.values():
            dictList.append({
                'wikiId': wikiUser.wikiId,
                'url':wikiUser.url,
                'scriptPath':wikiUser.scriptPath,
                'version':wikiUser.version
            })
        html=render_template("tableview.html",title="Wikis",dictList=dictList)
        return html    
    
    def family(self)->str:
        '''
        show a html representation of the family of wikis on this server (if any)
        '''
        dictList=[]
        family=LocalWiki.getFamily()
        for siteName in family:
            localWiki=family[siteName]
            dictList.append({
                'site': localWiki.siteName,
                'logo': localWiki.logo
            })
        html=render_template("tableview.html",title="Wiki Family",dictList=dictList)
        return html
        
    def wrap(self,siteName,path):
        '''
        wrap the given path for the given site
        Args:
            siteName(str): the name of the site to wrap
            path(path): the path to wrap
        '''
        content=None
        template="index.html"
        title="Error"
        if not siteName in self.enabledSites:
            error="access to site '%s' is not enabled you might want to add it via the --sites command line option" % siteName
        else:
            frontend=self.frontends.get(siteName) 
            if frontend.needsProxy(path):
                return frontend.proxy(path)
            else:
                title,content,error=frontend.getContent(path);
                template=frontend.site.template
        return render_template(template,title=title,content=content,error=error)
       
    def run(self):
        '''
        start the flask webserver
        '''
        self.app.run(debug=self.debug,port=self.port,host=self.host)   
        pass
        