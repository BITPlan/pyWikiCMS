'''
Created on 27.07.2020

@author: wf
'''

class Frontend(object):
    '''
    Wiki Content Mangement System Frontend
    '''
    def __init__(self, wikiid, debug=False):
        '''
        Constructor
        '''
        self.wikiid=wikiid
        self.debug=debug
        
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
            content=pagePath
        return content,error
        