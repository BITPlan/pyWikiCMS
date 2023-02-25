'''
Created on 2022-12-03

@author: wf
'''
import asyncio
from wikibot3rd.wikiuser import WikiUser
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.smw import SMWClient
from jpwidgets.bt5widgets import Link, Switch
from jpwidgets.widgets import LodGrid
from frontend.html_table import HtmlTables
from lodstorage.lod import LOD
import os
import glob
import time
from pathlib import Path

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
    
class WikiCheck:
    """
    
    """
    def __init__(self,name,func,checked:bool=True):
        """
        constructor
        """
        self.name=name
        self.func=func
        self.checked=checked
        
    def radio_changed(self,msg):
        """
        react on a changed radio button
        """
        self.checked=not msg["target"].checked
        msg["target"].checked=self.checked
        pass
        
    def asRadioButton(self,jp,a):
        """
        """
        label = jp.Label(classes='inline-block mb-1 p-1', a=a)
        radio_btn = jp.Input(type='radio', name=self.name, value=self.name, a=label, click=self.radio_changed,checked=self.checked)
        jp.Span(classes='ml-1', a=label, text=self.name)
        return radio_btn
    
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
        self.setupWikiUsers()
        self.addCheckButtons(a=a)
        self.agGrid=LodGrid(a=a)
        self.agGrid.theme="ag-theme-material"
        self.lod=[]
        self.lodindex={}
        for index,wikiUser in enumerate(self.sortedWikiUsers):
            self.lod.append({
                "#": index+1,
                "wiki": Link.newTab(url=wikiUser.getWikiUrl(), text=wikiUser.wikiId),
                "version": wikiUser.version,
                "since": "",
                "until": "",
                "pages": "",
                "backup": "",
                "age": ""
            })
            self.lodindex[wikiUser.wikiId]=index+1
        self.setDefaultColDef(self.agGrid)
        self.agGrid.load_lod(self.lod)
        #self.agGrid.options.columnDefs[0].checkboxSelection = True
        self.agGrid.html_columns=[1]
    
    def setupWikiUsers(self):
        # wiki users
        self.wikiUsers=WikiUser.getWikiUsers()
        self.sortedWikiUsers=sorted(self.wikiUsers.values(),key=lambda w:w.wikiId)
        self.wikiClients={}
        self.smwClients={}           
       
    def addCheckButtons(self,a):
        self.wikiChecks=[
            WikiCheck("version",self.checkWikiVersion4WikiUser),
            WikiCheck("backup",self.checkBackup4WikiUser),
            WikiCheck("pages",self.checkPages4WikiUser)
        ]
        for wikiCheck in self.wikiChecks:
            wikiCheck.asRadioButton(self.jp, a=a)
        button_classes="btn btn-primary"
        self.jp.Button(text="Checks",a=a,classes=button_classes,click=self.performWikiChecks)
  
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
    
    def getRowForWikiId(self,wikiId):
        for row in self.lod:
            if row["#"]==self.lodindex[wikiId]:
                return row
        else:
            return None
        
    async def updateRow(self,row,key,value):
        """
        update a row in the grid
        """
        row[key]=value
        for grid_row in self.agGrid.options.rowData:
            if row["#"]==grid_row["#"]:
                grid_row[key]=value
                break

    async def performWikiChecks(self,_msg):
        try:
            for wikiUser in self.sortedWikiUsers:
                for wikiCheck in self.wikiChecks:
                    if wikiCheck.checked:
                        await wikiCheck.func(wikiUser)
                await self.app.wp.update()
        except BaseException as ex:
            self.app.handleException(ex)
            
    async def checkPages4WikiUser(self,wikiUser):
        """
        try login for wikUser and report success or failure
        """
        try:
            row=self.getRowForWikiId(wikiUser.wikiId)
            wikiClient=WikiClient.ofWikiUser(wikiUser)
            self.wikiClients[wikiUser.wikiId]=wikiClient
            try: 
                smwClient=SMWClient(wikiClient.getSite())
                self.smwClients[wikiUser.wikiId]=smwClient
            except Exception as ex:
                await self.updateRow(row, "login", f"❌ {str(ex)}")
                await self.updateRow(row, "pages", "❌")
                return 
            smwClient=self.smwClients[wikiUser.wikiId]
            askQuery="""{{#ask: [[Modification date::+]]
|format=count
}}"""
            result=list(smwClient.query(askQuery))
           
            pass
        except BaseException as ex:
            self.app.handleException(ex)
            
    async def checkWikiVersion4WikiUser(self,wikiUser):
        """
        """
        try:
            mw_version=self.checkVersion(wikiUser.getWikiUrl())
            if not mw_version.startswith("MediaWiki"):
                mw_version=f"MediaWiki {mw_version}"
            row=self.getRowForWikiId(wikiUser.wikiId)
            ex_version=row["version"]
            if ex_version==mw_version:
                await self.updateRow(row, "version",f"{mw_version}✅")
            else:
                await self.updateRow(row,"version",f"{ex_version}!={mw_version}❌")
        except BaseException as ex:
            self.app.handleException(ex)
            
    async def checkBackup4WikiUser(self,wikiUser):
        """
        """
        try:
            row=self.getRowForWikiId(wikiUser.wikiId)
            backupPath=f"{Path.home()}/wikibackup/{wikiUser.wikiId}"
            if os.path.isdir(backupPath):
                wikiFiles = glob.glob(f"{backupPath}/*.wiki") 
                msg=f"{len(wikiFiles):6} ✅"
                await self.updateRow(row, "backup", msg)
                #https://stackoverflow.com/a/39327156/1497139
                if len(wikiFiles)>0:
                    latest_file = max(wikiFiles, key=os.path.getctime)
                    st=os.stat(latest_file)
                    age_days=round((time.time()-st.st_mtime)/86400)
                    await self.updateRow(row, "age",f"{age_days}")
            else:
                msg="❌"
                await self.updateRow(row, "backup", msg)
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