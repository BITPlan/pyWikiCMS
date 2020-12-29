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
        '''
        self.wikiId=wikiId
        self.debug=debug
        self.defaultPage=defaultPage
        
    def open(self):
        '''
        open the frontend
        '''
        self.wikiclient=WikiClient.ofWikiId(self.wikiId)
        
    def errMsg(self,ex):
        if self.debug:
            msg="%s\n%s" % (repr(ex),traceback.format_exc())
        else:
            msg=repr(ex)
        return msg
    
    def wikiPage(self,pagePath):
        if "/index.php/" in pagePath:
            wikipage=pagePath.replace("/index.php/","")
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
        if self.debug:
            print (pagePath)
        illegalChars=['{','}','<','>','[',']','|']
        for illegalChar in illegalChars:
            if illegalChar in pagePath:
                error="invalid char %s in given pagePath " % (illegalChar)
        return error;
            
    def getContent(self,pagePath):
        ''' get the content for the given pagePath '''
        content=None
        error=self.checkPath(pagePath)
        if error is None:
            try:
                if pagePath=="":
                    pageTitle=self.defaultPage
                else:
                    pageTitle=self.wikiPage(pagePath)
                content=self.wikiclient.getHtml(pageTitle)
            except Exception as e:
                error=self.errMsg(e)
        return content,error
        