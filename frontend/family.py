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
        
        
    @staticmethod
    def getFamily(sitedir="/var/www/mediawiki/sites"):
        '''
        get a dict of local wikis on this server
        '''
        family={}
        for folder in os.listdir(sitedir):
            lsettings="%s/%s/LocalSettings.php" % (sitedir,folder)
            if os.path.isfile(lsettings):
                localWiki=LocalWiki(folder,lsettings)
                family[folder]=localWiki
                
        return family
        