'''
Created on 2021-01-01

@author: wf
'''
import os
import re
import socket
import requests
from pathlib import Path

class LocalWiki(object):
    '''
    a local Wiki
    '''

    def __init__(self,siteName:str,family=None,localSettings:str=None):
        '''
        Constructor
        
        Args:
            siteName(str): the name of the site
            localSettings(str): path to the LocalSettings.php (if any) 
        '''
        self.siteName=siteName
        try:
            self.ip=socket.gethostbyname(self.siteName)
        except Exception:
            self.ip="?"
            pass
        self.siteId=siteName.split(".")[0]
        self.family=family
        self.localSettings=localSettings
        if self.localSettings is None:
            self.settingLines=[]
        else:
            with open(localSettings) as f:
                self.settingLines = f.readlines()
            self.logo=self.getSetting("wgLogo")
            self.database=self.getSetting("wgDBname")
            self.url=self.getSetting("wgServer")
            self.dbUser=self.getSetting("wgDBuser")
            self.dbPassword=self.getSetting("wgDBpassword")
            self.scriptPath=self.getSetting("wgScriptPath")
            if self.scriptPath is None:
                self.scriptPath=""
            self.url="%s%s/" % (self.url,self.scriptPath)
            self.statusCode=self.getStatusCode()
            

    def getStatusCode(self,timeout=0.5):
        '''
        get the status Code for my url
        
        Args:
            timeout(float): the maximum time to wait for a response
            
        Returns:
            int: html statusCode or -1 if there was a timeout
        '''
        statusCode=-1
        try:
            page = requests.get(self.url,verify=False,timeout=timeout)
            statusCode=page.status_code
        except Exception:
            pass
        return statusCode
        
    def getSetting(self,varName:str)->str:
        '''
        get the setting of the given variableName from the LocalSettings.php
        
        Args:
            varName(str): the name of the variable to return
        Returns:
            str: the value of the variable
        '''
        pattern=r'[^#]*\$%s\s*=\s*"(.*)"' % varName
        for line in self.settingLines:
            m=re.match(pattern,line)
            if m:
                value=m.group(1)
                return value
        return None
    
    def getLogo(self)->str:
        '''
        get the local path to the logo file of this wiki
        
        Returns:
            str: the logo path if logo is defined as file else None
        '''
        logoPath=self.logo
        # work around wgResourceBasePath
        logoPath=logoPath.replace("$wgResourceBasePath","")
        logoPath=logoPath.replace("/images/%s/" % self.siteId,"/images/")
        if logoPath.startswith("/") and self.family:
            logoFile="%s/%s%s" % (self.family.sitedir,self.siteName,logoPath)
        else:
            logoFile=None
        return logoFile
    
class WikiBackup(object):
    '''
    find out details about a WikiBackup
    
    potentially this class needs to move upstream to py-3rdparty-MediaWiki
    '''
    
    def __init__(self,wikiuser):
        '''
        constructor
        
        Arguments:
            wikiuser(WikiUser): the wikiuser to access this backup
        '''
        self.wikiuser=wikiuser
        home=str(Path.home())
        self.backupPath='%s/wikibackup/%s' % (home,wikiuser.wikiId)
        self.gitPath="%s/.git" % self.backupPath
        pass
    
    def exists(self)->bool:
        '''
        check if this Backup exists
        
        Returns:
            bool: True if the self.backupPath directory exists
        '''
        return os.path.isdir(self.backupPath)
    
    def hasGit(self)->bool:
        '''
        check if this Backup has a local git repository
        
        Returns:
            bool: True if the self.gitPath directory exists
        '''
        return os.path.isdir(self.gitPath)
        
    
class WikiFamily(object):
    '''
    the wiki family found in the given site dir
    '''
    
    def __init__(self,sitedir:str="/var/www/mediawiki/sites"):    
        '''
        constructor
        Args:
            sitedir(str): the path to the site definitions
            see http://wiki.bitplan.com/index.php/Wiki_Family
        '''
        self.family={}
        self.sitedir=sitedir
        if os.path.isdir(sitedir):
            for siteName in os.listdir(sitedir):
                lsettings="%s/%s/LocalSettings.php" % (sitedir,siteName)
                if os.path.isfile(lsettings):
                    localWiki=LocalWiki(siteName,self,lsettings)
                    self.family[siteName]=localWiki
       
        
        