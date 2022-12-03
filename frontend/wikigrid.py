'''
Created on 2022-12-03

@author: wf
'''
import asyncio
from wikibot.wikiuser import WikiUser
from jpwidgets.bt5widgets import Link, Switch
from jpwidgets.widgets import LodGrid
from frontend.html_table import HtmlTables
from lodstorage.lod import LOD

class Display:
    '''
    generic Display
    '''
    noneValue="-"
    
    def setDefaultColDef(self,agGrid):
        """
        set the default column definitions
        """
        defaultColDef=agGrid.options.defaultColDef
        defaultColDef.resizable=True
        defaultColDef.sortable=True
        defaultColDef.filter=True
        # https://www.ag-grid.com/javascript-data-grid/grid-size/
        defaultColDef.wrapText=True
        defaultColDef.autoHeight=True
        defaultColDef.headerClass="font-bold"
        
    def addFitSizeButton(self,a):
        self.onSizeColumnsToFitButton=Switch(
            a=a,
            labelText="fit",
            checked=False
            #iconName='format-columns',
            #classes="btn btn-primary btn-sm col-1"
        )
        self.onSizeColumnsToFitButton.on("input",self.onSizeColumnsToFit)
        
    async def onSizeColumnsToFit(self,_msg:dict):   
        try:
            await asyncio.sleep(0.2)
            if self.agGrid:
                await self.agGrid.run_api('sizeColumnsToFit()', self.app.wp)
        except Exception as ex:
            self.app.handleException(ex)
    
    
class WikiGrid(Display):
    """
    grid of Wikis
    """
    
    def __init__(self,a,app):
        """
        constructor
        
        Args:
            targets(dict): a list of targets
            a: the parent element
            app: the parent app
            
        """
        self.app=app
        self.jp=app.jp
        # wiki users
        self.wikiUsers=WikiUser.getWikiUsers()
        self.sortedWikiUsers=sorted(self.wikiUsers.values(),key=lambda w:w.wikiId)
        self.jp.Button(text="Check Versions",a=a,click=self.checkVersions)
        self.agGrid=LodGrid(a=a)
        self.agGrid.theme="ag-theme-material"
        self.lod=[]
        self.lodindex={}
        for index,wikiUser in enumerate(self.sortedWikiUsers):
            self.lod.append({
                "#": index+1,
                "wiki": Link.newTab(url=wikiUser.getWikiUrl(), text=wikiUser.wikiId),
                "mw version": wikiUser.version 
            })
            self.lodindex[wikiUser.wikiId]=index+1
        self.setDefaultColDef(self.agGrid)
        self.agGrid.load_lod(self.lod)
        #self.agGrid.options.columnDefs[0].checkboxSelection = True
        self.agGrid.html_columns=[1]
        
    def checkVersion(self,wikiUrl:str):
        """
        check the mediawiki version
        """
        version_url=f"{wikiUrl}/index.php/Special:Version"
        mw_version="?"
        try:
            html_tables=HtmlTables(version_url)
            tables=html_tables.get_tables("h2")      
            if "Installed software" in tables:
                software=tables["Installed software"]
                software_map,_dup=LOD.getLookup(software, "Product", withDuplicates=False)
                mw_version=software_map["MediaWiki"]["Version"]
        except Exception as ex:
            mw_version=f"error: {str(ex)}"
        return mw_version
    
    async def checkVersions(self,_msg):
        try:
            for wikiUser in self.sortedWikiUsers:
                mw_version=self.checkVersion(wikiUser.getWikiUrl())
                for row in self.lod:
                    if row["#"]==self.lodindex[wikiUser.wikiId]:
                        ex_version=row["mw version"]
                        if ex_version==mw_version:
                            row["mw version"]=f"{mw_version}✅"
                        else:
                            row["mw version"]=f"{ex_version}!={mw_version}❌"
                self.agGrid.load_lod(self.lod)
                await self.app.wp.update()
            pass
        except BaseException as ex:
            self.app.handleException(ex)
        
    async def onPageReady(self,_msg):
        """
        react on page Ready
        """
        try:
            pass
        except BaseException as ex:
            self.app.handleException(ex)
        