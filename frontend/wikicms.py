'''
Created on 27.07.2020

@author: wf
'''
from wikibot.wikiclient import WikiClient
import traceback

class Frontend(object):
    '''
    Wiki Content Management System Frontend
    '''
    def __init__(self, wikiId,defaultPage="Main Page", debug=False):
        '''
        Constructor
        Args:
            wikiId(str): the id of the wiki this frontend is for
            defaultPage(str): the default page of this frontend
        '''
        self.wikiId=wikiId
        self.debug=debug
        self.defaultPage=defaultPage
        self.wikiclient=None
        
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
        if self.wikiclient is None:
            self.wikiclient=WikiClient.ofWikiId(self.wikiId)
            self.wikiclient.login()
        
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
            
    def getContent(self,pagePath):
        ''' get the content for the given pagePath 
        Args:
            pagePath(str): the page Pageh
        Returns:
            str: the HTML content for the given path
        '''
        content=None
        error=None
        try:
            if pagePath=="":
                pageTitle=self.defaultPage
            else:
                error=self.checkPath(pagePath)
                pageTitle=self.wikiPage(pagePath)
            if error is None:
                content=self.wikiclient.getHtml(pageTitle)
        except Exception as e:
            error=self.errMsg(e)
        return content,error
        