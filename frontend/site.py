'''
Created on 2020-12-31

@author: wf
'''
import jinja2
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
        if "templateFolder" in config:
            self.templateFolder=config['templateFolder']
        else:
            self.templateFolder=self.name
        if "packageName" in config:
            self.packageName=config["packageName"]
        else:
            self.packageName=self.name
        if "packageFolder" in config:
            self.packageFolder=config["packageFolder"]
        else:
            self.packageFolder=self.name
        self.configured=True
            
    def open(self):
        '''
        open this site
        '''
        if not self.configured:
            raise Exception("need to configure site before opening it")
        # https://stackoverflow.com/a/14276993/1497139
        # http://code.nabla.net/doc/jinja2/api/jinja2/loaders/jinja2.loaders.PackageLoader.html
        self.templateEnv=None
        if self.debug:
            print("adding %s to PYTHON PATH" % self.packageFolder)
        sys.path.insert(1,self.packageFolder)
        try:
            self.templateEnv = jinja2.Environment( loader=jinja2.PackageLoader(self.packageName, self.templateFolder))
        except Exception as ex:
            self.error=ex
        
    