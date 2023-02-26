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
import sys

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
        
        self.wikiGrid=None
        
        jp.Route('/settings',self.settings)
        jp.Route('/about',self.about)
        
    async def onPageReady(self,_msg):
        """
        react on page Ready
        """
        try:
            if self.wikiGrid is not None:
                await self.wikiGrid.onPageReady(_msg)
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
        self.rowF=self.jp.Div(classes="row",a=self.contentbox)
        # columns
        self.colA1=self.jp.Div(classes="col-12",a=self.rowA)
        self.colC1=self.jp.Div(classes="col-12",a=self.rowC)
        self.colD1=self.jp.Div(classes="col-3",a=self.rowD)
        self.colD2=self.jp.Div(classes="col-2",a=self.rowD)
        self.colE1=self.jp.Div(classes="col-12",a=self.rowE)
        self.colF1=self.jp.Div(classes="col-12",a=self.rowF)
        # standard elements
        self.errors=self.jp.Div(a=self.colA1,style='color:red')
        self.messages=self.jp.Div(a=self.colE1,style='color:black')  
        self.progressBar = ProgressBar(a=self.rowD)
    
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
        self.aboutDiv=About(a=self.colC1,version=self.version)

        return self.wp
    
    def logo_img(self,a,logo,logo_size):
        markup=f"""<img class='rounded' src='{logo}' height='{logo_size}' width='{logo_size}'>"""
        logo_div=self.jp.Div(a=a,classes="col-1")#
        logo_div.inner_html=markup
    
    def addServerInfo(self,a):
        """
        add ServerInfo
        """
        infoDiv=self.jp.Div(a=a,classes='col-2 h4 align-middle')
        if sys.platform == "linux" or sys.platform == "linux2":
            # linux
            os_logo="https://upload.wikimedia.org/wikipedia/commons/a/af/Tux.png"
        elif sys.platform == "darwin":
            # OS X
            os_logo="https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Icon-Mac.svg/256px-Icon-Mac.svg.png"
        elif sys.platform == "win32":
            # Windows...
            os_logo="https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Windows_icon.svg/256px-Windows_icon.svg.png"
        else:
            os_logo=""
        logo_size=64
        infoDiv.inner_html=f"<span>Welcome to {self.args.host}</span>"
        self.logo_img(a,os_logo,logo_size)
        self.logo_img(a,self.args.logo,logo_size)
        pass
    
    async def content(self)->"jp.WebPage":
        '''
        provide the main content page
        
        Returns:
            jp.WebPage: a justpy webpage renderer
        '''
        self.setupRowsAndCols()
        self.addServerInfo(a=self.rowB)
        self.wikiGrid=WikiGrid(a=self.colC1,app=self)
        self.wp.on("page_ready", self.onPageReady)
        return self.wp
    
    def start(self,host,port,debug):
        """
        start the server
        """
        self.debug=debug
        import justpy as jp
        jp.justpy(self.content,host=host,port=port)
