'''
Created on 27.07.2020

@author: wf
'''
from wikibot.wikibot import WikiBot

class Frontend(object):
    '''
    Wiki Content Mangement System Frontend
    '''
    def __init__(self, wikiId, debug=False):
        '''
        Constructor
        '''
        self.wikiId=wikiId
        self.debug=debug
        
    def open(self):
        self.wikibot=WikiBot.ofWikiId(self.wikiId)
        
    def getContent(self,pagePath):
        ''' get the content for the given pagePath '''
        error=None
        content=None
        if self.debug:
            print (pagePath)
        illegalChars=['{','}','<','>','[',']','|']
        for illegalChar in illegalChars:
            if illegalChar in pagePath:
                error="invalid char %s in given pagePath " % (illegalChar)
        if error is None:
            page=self.wikibot.getPage(pagePath)
            if page is not None:
                content=page.text
        return content,error
        