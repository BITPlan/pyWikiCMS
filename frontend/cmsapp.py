'''
Created on 2022-11-03

@author: wf
'''
import os
from jpcore.compat import Compatibility;Compatibility(0,11,3)
from jpcore.justpy_config import JpConfig
script_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = script_dir+"/resources/static"
JpConfig.set("STATIC_DIRECTORY",static_dir)
# shut up justpy
JpConfig.set("VERBOSE","False")
JpConfig.setup()
from jpwidgets.bt5widgets import App,About,ProgressBar
from frontend.wikigrid import WikiGrid

class CmsApp(App):
    """
    Content Management System application
    """
    
    def __init__(self,version,title:str,args:None):
        '''
        Constructor
        
        Args:
            version(Version): the version info for the app
        '''
        import justpy as jp
        self.jp=jp
        App.__init__(self, version=version,title=title)
        self.args=args
        self.addMenuLink(text='Home',icon='home', href="/")
        self.addMenuLink(text='github',icon='github', href=version.cm_url)
        self.addMenuLink(text='Chat',icon='chat',href=version.chat_url)
        self.addMenuLink(text='Documentation',icon='file-document',href=version.doc_url)
        self.addMenuLink(text='Settings',icon='cog',href="/settings")
        self.addMenuLink(text='About',icon='information',href="/about")
        
        jp.Route('/settings',self.settings)
        jp.Route('/about',self.about)
        
    async def onPageReady(self,_msg):
        """
        react on page Ready
        """
        try:
            pass
            #if len(self.gridRows.components)==0:
            #    await self.showGenerateGrid()
        except BaseException as ex:
            self.handleException(ex)
        
    def setupRowsAndCols(self):
        """
        setup the general layout
        """
        head_html="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">"""
        self.wp=self.getWp(head_html)
        self.button_classes = """btn btn-primary"""
        # rows
        self.rowA=self.jp.Div(classes="row",a=self.contentbox)
        self.rowB=self.jp.Div(classes="row",a=self.contentbox)
        self.rowC=self.jp.Div(classes="row",a=self.contentbox)
        self.rowD=self.jp.Div(classes="row",a=self.contentbox)
        self.rowE=self.jp.Div(classes="row",a=self.contentbox)
        # columns
        self.colA1=self.jp.Div(classes="col-12",a=self.rowA)
        self.colB1=self.jp.Div(classes="col-12",a=self.rowB)
        self.colC1=self.jp.Div(classes="col-3",a=self.rowC)
        self.colC2=self.jp.Div(classes="col-2",a=self.rowC)
        self.colD1=self.jp.Div(classes="col-12",a=self.rowD)
        self.colE1=self.jp.Div(classes="col-12",a=self.rowE)
        # standard elements
        self.errors=self.jp.Div(a=self.colA1,style='color:red')
        self.messages=self.jp.Div(a=self.colE1,style='color:black')  
        self.progressBar = ProgressBar(a=self.rowC)

    
    async def settings(self)->"jp.WebPage":
        '''
        settings
        
        Returns:
            jp.WebPage: a justpy webpage renderer
        '''
        self.setupRowsAndCols()
        return self.wp
    
    async def about(self)->"jp.WebPage":
        '''
        show about dialog
        
        Returns:
            jp.WebPage: a justpy webpage renderer
        '''
        self.setupRowsAndCols()
        self.aboutDiv=About(a=self.colB1,version=self.version)

        return self.wp
    
    async def content(self)->"jp.WebPage":
        '''
        provide the main content page
        
        Returns:
            jp.WebPage: a justpy webpage renderer
        '''
        self.setupRowsAndCols()
        self.wikiGrid=WikiGrid(a=self.colB1,app=self)
        self.wp.on("page_ready", self.onPageReady)
        return self.wp
    
    def start(self,host,port,debug):
        """
        start the server
        """
        self.debug=debug
        import justpy as jp
        jp.justpy(self.content,host=host,port=port)
