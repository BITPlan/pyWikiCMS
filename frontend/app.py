'''
Created on 2020-12-30

@author: wf
'''
from flask import Flask
from frontend.wikicms import Frontend
from flask import render_template
import os

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
        self.frontends={}
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
            delim=""
            for part in parts[1:]:
                path=path+"%s%s" % (delim,part)
                delim="/"
        return site,path    
    
    def enableSites(self,sites):
        '''
        enable the sites given in the sites list
        Args:
            sites(list): a list of strings with wikiIds to be enabled
        '''
        self.enabledSites.extend(sites)
        
    def wrap(self,site,path):
        '''
        wrap the given path for the given site
        Args:
            site(str): the site to wrap
            path(path): the path to wrap
        '''
        content=None
        if not site in self.enabledSites:
            error="access to site '%s' is not enabled you might want to add it via the --sites command line option" % site
        else:
            if site=="admin":
                error=None
                content="admin site"
            else:
                if not site in self.frontends:
                    self.frontends[site]=Frontend(site)
                
                frontend=self.frontends[site]     
                frontend.open()     
                content,error=frontend.getContent(path);
        return render_template('index.html',content=content,error=error)
       
    def run(self):
        '''
        start the flask webserver
        '''
        self.app.run(debug=self.debug,port=self.port,host=self.host)   
        pass
        