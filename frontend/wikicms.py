'''
Created on 2020-07-27

@author: wf
'''
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.smw import SMWClient
from frontend.site import Site
from bs4 import BeautifulSoup
import traceback
from http.client import HTTPConnection
from urllib.parse import urlparse

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
        
    def open(self,appWrap=None):
        '''
        open the frontend
        
        Args:
             appWrap(appWrap): optional fb4 Application Wrapper
        '''
        self.appWrap=appWrap
        if self.wiki is None:
            self.wiki=WikiClient.ofWikiId(self.site.wikiId)
            self.wiki.login()
            self.smwclient=SMWClient(self.wiki.getSite())
            self.site.open(appWrap)
        
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
    
    def proxy(self, path: str) -> str:
        """
        Proxy a request.
        See https://stackoverflow.com/a/50231825/1497139
        
        Args:
            path (str): the path to proxy
            
        Returns:
            the proxied result as a string
        """
        wikiUser = self.wiki.wikiUser
        url = f"{wikiUser.url}{wikiUser.scriptPath}{path}"

        # Parse the URL to get domain and path
        parsed_url = urlparse(url)
        connection = HTTPConnection(parsed_url.netloc)

        # Make the GET request
        connection.request("GET", parsed_url.path + "?" + parsed_url.query)

        # Get the response
        response = connection.getresponse()

        # Read the content
        content = response.read()

        # Assuming you want to return the content as a byte string,
        # otherwise you may need to decode it to a string depending on the expected return type
        # content = content.decode()

        # Close the connection
        connection.close()

        return content
    
    def filter(self,html):
        return self.doFilter(html,self.filterKeys)
    
    def fixNode(self,node,attribute,prefix,delim=None):
        '''
        fix the given node
        
        node(BeautifulSoup): the node
        attribute(str): the name of the attribute e.g. "href", "src"
        prefix(str): the prefix to replace e.g. "/", "/images", "/thumbs"
        delim(str): if not None the delimiter for multiple values
        '''
        siteprefix="/%s%s" % (self.site.name,prefix)
        if attribute in node.attrs:
            attrval=node.attrs[attribute]
            if delim is not None:
                vals=attrval.split(delim)
            else:
                vals=[attrval]
                delim=""
            newvals=[]
            for val in vals:    
                if val.startswith(prefix):
                    newvals.append(val.replace(prefix,siteprefix,1))
                else:
                    newvals.append(val)
            if delim is not None:
                node.attrs[attribute]=delim.join(newvals)
    
    def fixImages(self,soup):
        for img in soup.findAll('img'):
            self.fixNode(img,"src","/")
            self.fixNode(img,"srcset","/",", ")
            
    
    def fixHtml(self,soup):
        '''
        fix the HTML in the given soup
        
        Args:
            soup(BeautifulSoup): the html parser
        '''
        self.fixImages(soup)
        # fix absolute hrefs
        for a in soup.findAll('a'):
            self.fixNode(a,"href","/")
        return soup
    
    def unwrap(self,soup):
        html=str(soup)
        html=html.replace("<html><body>","")
        html=html.replace("</body></html>","")
        return html
        
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
            for s in soup.select('span.mw-editsection'):
                s.extract()
        return soup
    
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
            if "invalid characters" in self.unwrap(ex):
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
                soup=self.filter(content)
                soup=self.fixHtml(soup)
                content=self.unwrap(soup)
        except Exception as e:
            error=self.errMsg(e)
        return pageTitle,content,error
        
    def toReveal(self,html):
        '''
        convert the given html to reveal
        '''
        soup = BeautifulSoup(html,'lxml')
        for h2 in soup.findChildren(recursive=True):
            if h2.name=="h2":
                span=h2.next_element
                if span.name=="span":
                    tagid=span.get('id')
                    if tagid.startswith("⌘⌘"):
                        section = soup.new_tag("section")
                        h2.parent.append(section)
                        section.insert(0,h2)
                        tag=h2.next_element
                        while (tag is not None and tag.name!="h2"):
                            if tag.parent!=h2:
                                section.append(tag)
                            tag=tag.next_element
        html=self.unwrap(soup)
        return html
        
    def render(self,path:str,**kwargs)->str:
        '''
        render the given path
        
        Args:
            path(str): the path to render the content for
            kwargs(): optional keyword arguments
            
        Returns:
            str: the rendered result
        '''
        if self.needsProxy(path):
            result=self.proxy(path)
        else:
            pageTitle, content, error = self.getContent(path);
            frame=self.getFrame(pageTitle)
            if frame is not None:
                template = "%s.html" % frame
                if frame == "reveal" and error is None:
                    content=self.toReveal(content)
            else:
                template = self.site.template
            if not 'title' in kwargs:
                kwargs['title']=pageTitle
            if not 'content' in kwargs:
                kwargs['content']=content
            if not 'error' in kwargs:
                kwargs['error']=error
            result=self.renderTemplate(template, **kwargs)
        return result