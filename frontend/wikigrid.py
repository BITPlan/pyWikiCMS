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
        button_classes="btn btn-primary"
        self.jp.Button(text="Check Version",a=a,classes=button_classes,click=self.checkVersions)
        self.jp.Button(text="Check Backup",a=a,classes=button_classes,click=self.checkBackups)
        self.agGrid=LodGrid(a=a)
        self.agGrid.theme="ag-theme-material"
        self.lod=[]
        self.lodindex={}
        for index,wikiUser in enumerate(self.sortedWikiUsers):
            self.lod.append({
                "#": index+1,
                "wiki": Link.newTab(url=wikiUser.getWikiUrl(), text=wikiUser.wikiId),
                "mw version": wikiUser.version,
                "wiki backup": "",
                "age": ""
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
        await self.app.wp.update()

    async def checkVersions(self,_msg):
        try:
            for wikiUser in self.sortedWikiUsers:
                mw_version=self.checkVersion(wikiUser.getWikiUrl())
                if not mw_version.startswith("MediaWiki"):
                    mw_version=f"MediaWiki {mw_version}"
                row=self.getRowForWikiId(wikiUser.wikiId)
                ex_version=row["mw version"]
                if ex_version==mw_version:
                    await self.updateRow(row, "mw version",f"{mw_version}✅")
                else:
                    await self.updateRow(row,"mw version",f"{ex_version}!={mw_version}❌")
            pass
        except BaseException as ex:
            self.app.handleException(ex)
            
    async def checkBackups(self,_msg):
        """
        """
        try:
            for wikiUser in self.sortedWikiUsers:
                row=self.getRowForWikiId(wikiUser.wikiId)
                backupPath=f"{Path.home()}/wikibackup/{wikiUser.wikiId}"
                if os.path.isdir(backupPath):
                    wikiFiles = glob.glob(f"{backupPath}/*.wiki")
                    #https://stackoverflow.com/a/39327156/1497139
                    latest_file = max(wikiFiles, key=os.path.getctime)
                    st=os.stat(latest_file)
                    age_days=round((time.time()-st.st_mtime)/86400)
                    msg=f"{len(wikiFiles):6} ✅"
                    await self.updateRow(row, "wiki backup", msg)
                    await self.updateRow(row, "age",f"{age_days}")
                else:
                    msg="❌"
                    await self.updateRow(row, "wiki backup", msg)
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
        