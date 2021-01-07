'''
Created on 2020-07-27

@author: wf
'''
from wikibot.wikiclient import WikiClient
from frontend.site import Site

import traceback

import requests
from flask import Response

class Frontend(object):
    '''
    Wiki Content Management System Frontend
    '''
    def __init__(self, siteName:str,debug:bool=False):
        '''
        Constructor
        Args:
            siteName(str): the name of the site this frontend is for
            defaultPage(str): the default page of this frontend
        '''
        
        self.site=Site(siteName)
        self.debug=debug
        self.wiki=None
        
    def log(self,msg):
        '''
        log the given message if debugging is true
        
        Args:
            msg(str): the message to log
        '''
        if self.debug:
            print(msg,flush=True)
        
    def open(self):
        '''
        open the frontend
        '''
        if self.wiki is None:
            self.wiki=WikiClient.ofWikiId(self.site.wikiId)
            #self.wiki.login()
        
    def errMsg(self,ex):
        if self.debug:
            msg="%s\n%s" % (repr(ex),traceback.format_exc())
        else:
            msg=repr(ex)
        return msg
    
    def wikiPage(self,pagePath):
        '''
        get the wikiPage for the given pagePath
        
        Args:
            pagePath(str): the page path
        Returns:
            str: the pageTitle
        '''
        if "/index.php/" in pagePath:
            wikipage=pagePath.replace("/index.php/","")
        elif pagePath.startswith("/"):
            wikipage=pagePath[1:]    
        else:
            wikipage=pagePath
        return wikipage
        
    
    def checkPath(self,pagePath):
        '''
        check the given pathPath
        
        Args:
            pagePath(str): the page Path to check
            
        Returns:
            str: None or an error message with the illegal chars being used
        '''
        error=None
        self.log(pagePath)
        illegalChars=['{','}','<','>','[',']','|']
        for illegalChar in illegalChars:
            if illegalChar in pagePath:
                error="invalid char %s in given pagePath " % (illegalChar)
        return error;
    
    def needsProxy(self,path:str)->bool:
        '''
        Args:
            path(str): the path to check
        Returns:
            True if this path needs to be proxied 
        '''
        result=path.startswith("/images")
        return result
    
    def proxy(self,path:str)->str:
        '''
        proxy a request
        see https://stackoverflow.com/a/50231825/1497139
        
        Args:
            path(str): the path to proxy
        Returns:
            the proxied result Request
        '''
        wikiUser=self.wiki.wikiUser
        url="%s%s%s" % (wikiUser.url,wikiUser.scriptPath,path)
        r = requests.get(url)
        return Response(r.content)
        
            
    def getContent(self,pagePath:str):
        ''' get the content for the given pagePath 
        Args:
            pagePath(str): the page Pageh
        Returns:
            str: the HTML content for the given path
        '''
        content=None
        error=None
        pageTitle="?"
        try:
            if pagePath=="/":
                pageTitle=self.site.defaultPage
            else:
                error=self.checkPath(pagePath)
                pageTitle=self.wikiPage(pagePath)
            if error is None:
                content=self.wiki.getHtml(pageTitle)
        except Exception as e:
            error=self.errMsg(e)
        return pageTitle,content,error
        