'''
Created on 2021-01-01

@author: wf
'''
import os
import re

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
            self.scriptPath=self.getSetting("wgScriptPath")
            if self.scriptPath is None:
                self.scriptPath=""
            self.url="%s%s" % (self.url,self.scriptPath)
        
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
       
        
        