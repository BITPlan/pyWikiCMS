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

    def __init__(self,siteName:str,localSettings:str=None):
        '''
        Constructor
        
        Args:
            siteName(str): the name of the site
            localSettings(str): path to the LocalSettings.php (if any) 
        '''
        self.siteName=siteName
        self.localSettings=localSettings
        if self.localSettings is None:
            self.settingLines=[]
        else:
            with open(localSettings) as f:
                self.settingLines = f.readlines()
            self.logo=self.getSetting("wgLogo")
            self.database=self.getSetting("wgDBname")
            self.url=self.getSetting("wgServer")
        
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
        for siteName in os.listdir(sitedir):
            lsettings="%s/%s/LocalSettings.php" % (sitedir,siteName)
            if os.path.isfile(lsettings):
                localWiki=LocalWiki(siteName,lsettings)
                self.family[siteName]=localWiki
                
    def getLogo(self,siteName:str):
        '''
        get the logo for the given siteName
        
        Args:
            siteName(str): the siteName e.g. wiki.bitplan.com
            
        Returns:
            str: the logo path if logo is defined as file else None
        '''
        localWiki = self.family[siteName]
        if localWiki.logo.startswith("/"):
            logoFile="%s/%s%s" % (self.sitedir,siteName,localWiki.logo)
        else:
            logoFile=None
        return logoFile
        
        