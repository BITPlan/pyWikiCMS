'''
Created on 2020-07-27

@author: wf
'''
from wikibot.wikiclient import WikiClient
from wikibot.smw import SMWClient
from frontend.site import Site
from bs4 import BeautifulSoup
import traceback
import requests
from flask import Response, render_template

class Frontend(object):
    '''
    Wiki Content Management System Frontend
    '''
    def __init__(self, siteName:str,debug:bool=False,filterKeys=None):
        '''
        Constructor
        Args:
            siteName(str): the name of the site this frontend is for
            debug: (bool): True if debugging should be on
            filterKeys: (list): a list of keys for filters to be applied e.g. editsection
        '''
        
        self.site=Site(siteName)
        self.debug=debug
        self.wiki=None
        if filterKeys is None:
            self.filterKeys=["editsection","parser-output"]
        else:
            self.filterKeys=[]
        
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
            self.wiki.login()
            self.smwclient=SMWClient(self.wiki.getSite())
            self.site.open()
        
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
        result=path.startswith("/images/")
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
    
    def filter(self,html):
        return self.doFilter(html,self.filterKeys)
        
    def doFilter(self,html,filterKeys):
        # https://stackoverflow.com/questions/5598524/can-i-remove-script-tags-with-beautifulsoup
        soup = BeautifulSoup(html,'lxml')
        if "parser-output" in filterKeys:
            parserdiv=soup.find('div',{"class": "mw-parser-output"})
            if parserdiv:
                soup=parserdiv
                pass
        # https://stackoverflow.com/questions/5041008/how-to-find-elements-by-class
        if "editsection" in filterKeys:
            for s in soup.select('span',{"class": "mw-editsection"}):
                s.extract()
        return str(soup)   
    
    def getFrame(self,pageTitle):
        '''
        get the frame template to be used for the given pageTitle#
        
        Args:
            pageTitle(str): the pageTitle to get the Property:Frame for
            
        Returns:
            str: the frame or None
        '''
        askQuery="""{{#ask: [[%s]]
|mainlabel=-
|?Frame=frame
}}
""" % pageTitle
        frame=None
        frameResult={}
        try:
            frameResult=self.smwclient.query(askQuery)
        except Exception as ex:
            if "invalid characters" in str(ex):
                pass
            else:
                raise ex
        if pageTitle in frameResult:
            frameRow=frameResult[pageTitle]
            frame=frameRow['frame']
            # legacy java handling
            if frame is not None:
                frame=frame.replace(".rythm","")
            pass
        return frame
            
    def getContent(self,pagePath:str):
        ''' get the content for the given pagePath 
        Args:
            pagePath(str): the pagePath
            whatToFilter(list): list of filter keys
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
                if self.wiki is None:
                    raise Exception("getContent without wiki - you might want to call open first")
                content=self.wiki.getHtml(pageTitle)
                content=self.filter(content)
        except Exception as e:
            error=self.errMsg(e)
        return pageTitle,content,error
    
    def renderTemplate(self,templateFile,args):
        '''
        render the given templateFile with the given arguments
        
        Args:
            templateFile(str): the template file to be used
            args(): same arguments a for dict constructor
            
        Returns:
            str: the rendered result
        '''
        if self.site.templateEnv is not None:
            template = self.site.templateEnv.get_template( templateFile )
            result=template.render(args)
            return result,None
        else:
            return None,self.site.error
        
    def render(self,path:str)->str:
        '''
        render the given path
        
        Args:
            path(str): the path to render the content for
            
        Returns:
            str: the rendered result
        '''
        if self.needsProxy(path):
            result=self.proxy(path)
        else:
            pageTitle, content, error = self.getContent(path);
            frame=self.getFrame(pageTitle)
            template = self.site.template
            result=render_template(template, title=pageTitle, content=content, error=error)
        return result