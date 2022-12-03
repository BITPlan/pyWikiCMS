'''
Created on 2022-12-03

@author: wf
'''
import asyncio
from wikibot.wikiuser import WikiUser
from jpwidgets.bt5widgets import Alert, App, IconButton, Switch, ProgressBar
from jpwidgets.widgets import LodGrid

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
        self.agGrid=LodGrid(a=a)
        self.agGrid.theme="ag-theme-material"
        lod=[]
        sortedWikis=sorted(self.wikiUsers.values(),key=lambda w:w.wikiId)
        for index,wikiUser in enumerate(sortedWikis):
            lod.append({
                "#": index+1,
                "wikiId":wikiUser.wikiId
            })
        self.setDefaultColDef(self.agGrid)
        self.agGrid.load_lod(lod)
        #self.agGrid.options.columnDefs[0].checkboxSelection = True
        self.agGrid.html_columns=[1]
        