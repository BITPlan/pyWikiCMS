'''
Created on 2020-12-31

@author: wf
'''
#import jinja2
import os
import sys

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
        self.template=config['template']
        if "packageName" in config:
            self.packageName=config["packageName"]
        else:
            self.packageName=self.name
        if "packageFolder" in config:
            self.packageFolder=config["packageFolder"]
        else:
            self.packageFolder=self.name
        self.configured=True
            
    def open(self,appWrap=None):
        '''
        open this site
        
        Args:
             appWrap(appWrap): optional fb4 Application Wrapper
        '''
        if not self.configured:
            raise Exception("need to configure site before opening it")
        # https://stackoverflow.com/a/14276993/1497139
        # http://code.nabla.net/doc/jinja2/api/jinja2/loaders/jinja2.loaders.PackageLoader.html
        if self.debug:
            print("adding %s to PYTHON PATH" % self.packageFolder)
        sys.path.insert(1,self.packageFolder)
        if appWrap is not None:
            templatePath="%s/%s/templates" % (self.packageFolder,self.packageName)
            if os.path.isdir(templatePath):
                appWrap.addTemplatePath(templatePath)
        # TODO: use a more elaborate loader concept if need be
        # self.templateEnv = jinja2.Environment( loader=jinja2.PackageLoader(self.packageName))
        
        pass
        
    