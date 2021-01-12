'''
Created on 2021-01-06

@author: wf
'''
from sys import platform
import os
import socket
import datetime
from flask import render_template
from lodstorage.jsonable import JSONAble
from pathlib import Path
from frontend.wikicms import Frontend
from sqlalchemy_utils import database_exists

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
        '''
        reinitialize me
        '''
        self.platform=platform
        self.uname=os.uname()
        self.name=self.uname[1]
        self.hostname=socket.getfqdn()
        self.ip=socket.gethostbyname(self.hostname)
        self.frontends={}
        self.siteLookup={}
        defaults={"sqlBackupPath":"/var/backup/sqlbackup"}
        for key,value in defaults.items():
            if not hasattr(self,key):
                self.__dict__[key]=value
        if Server.homePath is None:
            self.homePath = str(Path.home())
        else:
            self.homePath=Server.homePath
            
    def sqlGetDatabaseUrl(self,dbname:str,username:str,password:str,hostname:str=None)->str:
        '''
        get the DatabaseUrl for the given database Name
        
        Args:
            dbname(str): the name of the database
            username(str): the username
            password(str): the password
            
        Returns:
            str: the url for sqlAlchemy in rfc1738 format e.g. mysql://dt_admin:dt2016@localhost:3308/dreamteam_db
        '''
        #http://docs.sqlalchemy.org/en/latest/dialects/mysql.html
        if hostname is None:
            hostname=self.hostname
        url="mysql+pymysql://%s:%s@%s/%s" % (username,password,hostname,dbname)
        return url
            
    def sqlDatabaseExist(self,dburl:str,)->bool:
        '''
        check if the database with the given name exists
        
  
        Args:
            dburl(str): rfd 1738 formatted database url e.g. mysql://dt_admin:dt2016@localhost:3308/dreamteam_db
            
        Returns:
            True if the database exists, else False
        '''
        dbExists=False
        try:
            dbExists=database_exists(dburl)
        except Exception:
            # bad luck
            pass
        return dbExists
        
            
    def sqlBackupStateAsHtml(self,dbName):
        '''
        get the backup state of the given sql backup
        
        Args:
           dbName(str): the name of the database to check
        
        Returns:
            html: backup State html representation
        '''
        backupState=self.sqlBackupState(dbName)
        mbSize=backupState['size']/1024/1024
        mdate=backupState['mdate']
        isoDate=mdate.strftime('%Y-%m-%d %H:%M:%S') if mdate else ""
        html="%s %s - %4d MB" % (self.stateSymbol(backupState['exists']),isoDate,mbSize)
        return html
            
    def sqlBackupState(self,dbName):
        '''
        get the backup state of the given sql backup
        
        Args:
           dbName(str): the name of the database to check
        
        Returns:
            dict: backup State
        
        '''
        fullBackup="%s/today/%s_full.sql" % (self.sqlBackupPath,dbName)
        size=0
        mdate=None
        exists=os.path.isfile(fullBackup)
        if exists:
            stat=os.stat(fullBackup)
            size=stat.st_size
            mtime=stat.st_mtime
            mdate=datetime.datetime.fromtimestamp(mtime)
        result={'size':size,'exists':exists,'mdate':mdate}
        return result
            
    def enableFrontend(self,siteName):
        '''
        enable the given frontend
        
        Args:
            siteName(str): the siteName of the frontend to enable
        Returns:
            Frontend: the configured frontend
        '''
        if self.frontendConfigs is None:
            raise Exception('No frontend configurations loaded yet')
        if siteName not in self.siteLookup:
            raise Exception('frontend for site %s not configured yet' % siteName)
        frontend = Frontend(siteName) 
        self.frontends[siteName]=frontend
        config=self.siteLookup[siteName]
        frontend.site.configure(config)
        frontend.open()
        return frontend
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
                siteName=config["site"]
                self.siteLookup[siteName]=config
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
    
    def stateSymbol(self,b:bool)->str:
        '''
        return the symbol for the given boolean state b
        
        Args:
            b(bool): the state to return a symbol for
            
        Returns:
            ✅ for True and ❌ for false
        '''
        symbol="✅" if b else "❌"
        return symbol
    
    def checkApacheConfiguration(self,conf,status='enabled')->str:
        '''
        check the given apache configuration and return an indicator symbol
        
        Args:
            conf(str): the name of the apache configuration
        
        Returns:
            a state symbol
        '''
        path="/etc/apache2/sites-%s/%s.conf" % (status,conf)
        confExists=os.path.isfile(path)
        stateSymbol=self.stateSymbol(confExists)
        return stateSymbol
    
    def render(self):
        '''
        render me 
        '''
        html=render_template('server.html',server=self)
        return html
        
        
        
    
        