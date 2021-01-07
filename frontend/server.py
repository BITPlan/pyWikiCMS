'''
Created on 2021-01-06

@author: wf
'''
from sys import platform
import os
from flask import render_template
from lodstorage.jsonable import JSONAble
from pathlib import Path

class Server(JSONAble):
    '''
    a server that might serve multiple wikis for a wikiFarm
    '''
    homePath=None
    def __init__(self):       

        '''
        Constructor
        
        Args:
            storePath(str): the path to load my configuration from (if any)
        '''
        self.frontendConfigs=None
        self.logo=None
        self.purpose=""
        self.reinit()
        
    def reinit(self):
        self.platform=platform
        self.uname=os.uname()
        self.name=self.uname[1]
        self.frontends={}
        self.siteLookup={}
        defaults={"sqlbackupPath":"/var/backup/sqlbackup"}
        for key,value in defaults.items():
            if not hasattr(self,key):
                self.key=value
        if Server.homePath is None:
            self.homePath = str(Path.home())
        else:
            self.homePath=Server.homePath
            
    def enable(self,frontend):
        '''
        enable the given frontend
        
        Args:
            frontend(Frontend): the frontend to enable
        '''
        if self.frontendConfigs is None:
            raise Exception('No frontend configurations loaded yet')
        site=frontend.site
        if site.name not in self.siteLookup:
            raise Exception('frontend for site %s not configured yet' % site.name)
        self.frontends[site.name]=frontend
        config=self.siteLookup[site.name]
        site.configure(config)
        frontend.open()
        pass
        
    def getFrontend(self,wikiId):
        '''
        get the frontend for the given wikiid
        
        Args:
            wikiId(str): the wikiId to get the frontend for
        
        Returns:
            Frontend: the frontend for this wikiId
        '''
        return self.frontends[wikiId]
            
    def load(self):
        '''
        load my front end configurations
        '''
        storePath=self.getStorePath()
        if os.path.isfile(storePath+".json"):
            self.restoreFromJsonFile(storePath)
            self.reinit()
            for config in self.frontendConfigs:
                site=config["site"]
                self.siteLookup[site]=config
        pass
        
    def getStorePath(self,prefix:str="serverConfig")->str:
        '''
        get the path where my store files are located
        Returns:
            path to .wikicms in the homedirectory of the current user
        '''
        iniPath=self.homePath+"/.wikicms"
        if not os.path.isdir(iniPath):
            os.makedirs(iniPath)
        storePath="%s/%s" % (iniPath,prefix)
        return storePath
         
    def store(self):
        if self.frontends is not None:
            storePath=self.getStorePath()
            self.storeToJsonFile(storePath,"frontendConfigs")
        
    def getPlatformLogo(self)->str:
        '''
        get the logo url for the platform this server runs on
        
        Returns:
            str: the url of the logo for the current operating system platform
        '''
        logos={
            'aix': "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/IBM_AIX_logo.svg/200px-IBM_AIX_logo.svg.png",
            'cygwin': "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Cygwin_logo.svg/200px-Cygwin_logo.svg.png",
            'darwin':  "https://upload.wikimedia.org/wikipedia/de/thumb/b/b1/MacOS-Logo.svg/200px-MacOS-Logo.svg.png",
            'linux':   "https://upload.wikimedia.org/wikipedia/commons/a/af/Tux.png",
            'win32':   "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Windows_logo_-_2012.svg/200px-Windows_logo_-_2012.svg.png",
            'unknown': "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Blue_question_mark.jpg/240px-Blue_question_mark.jpg"
        }
        if self.platform in logos:
            logo=logos[self.platform]
        else:
            logo=logos['unknown']
        return logo
    
    def render(self):
        '''
        render me 
        '''
        html=render_template('server.html',server=self)
        return html
        
        
        
    
        