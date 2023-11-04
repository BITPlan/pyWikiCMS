'''
Created on 2020-12-31

@author: wf
'''

class Site(object):
    '''
    migrated from:
    https://github.com/BITPlan/com.bitplan.wikifrontend/blob/master/src/main/java/com/bitplan/wikifrontend/Site.java
    '''

    def __init__(self,name:str,defaultPage:str="Main Page",lang:str="en", debug=False):
        '''
        Constructor
        
        Args:
            name(str): the name of this site
            defaultPage(str): the default Page of this site
            lang(str): the default language of this site
            debug(bool): True if debug info should be given
        '''
        self.name=name
        self.defaultPage=defaultPage
        self.lang=lang
        self.configured=False
        self.debug=debug
        
    def configure(self,config:dict):
        '''
        configure me from the given configuration
        Args:
            config(dict): the configuration to use
        '''
        self.wikiId=config['wikiId']
        self.defaultPage=config['defaultPage']
        self.configured=True
            
    def open(self,ws=None):
        '''
        open this site
        
        Args:
             ws: Nicegui Webserver
        '''
        if not self.configured:
            raise Exception("need to configure site before opening it")      
        self.ws=ws
        
    