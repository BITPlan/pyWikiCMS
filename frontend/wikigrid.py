"""
Created on 2022-12-03

@author: wf
"""
import glob
import os
import time
from pathlib import Path

from frontend.mediawiki_site import MediaWikiSite
from ngwidgets.lod_grid import ListOfDictsGrid, GridConfig
from ngwidgets.progress import NiceguiProgressbar
from ngwidgets.widgets import Link
from ngwidgets.task_runner import TaskRunner
from nicegui import ui
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.wikiuser import WikiUser
from wikibot3rd.wikipush import WikiPush

from frontend.family import WikiBackup

class WikiState:
    """
    the state of a wiki
    """

    def __init__(self, row_index, wiki_user):
        """
        constructor
        """
        self.row_no = row_index + 1
        self.wiki_user = wiki_user
        self.wiki_backup = WikiBackup(wiki_user)
        self._wiki_client=None
        self.task_runner=TaskRunner()

    @property
    def wiki_client(self)->WikiClient:
        if not self._wiki_client:
            self._wiki_client= WikiClient.ofWikiUser(self.wiki_user)
        return self._wiki_client


    def as_dict(self):
        url = f"{self.wiki_user.url}{self.wiki_user.scriptPath}"
        link = Link.create(url=url, text=self.wiki_user.wikiId, target="_blank")

        record = {
            "#": self.row_no,
            "wiki": link,
            "version": self.wiki_user.version,
            "pages": "",
            "backup": "✅" if self.wiki_backup.exists() else "❌",
            "git": "✅" if self.wiki_backup.hasGit() else "❌",
            "age": "",
            "login": "",
        }
        return record


class WikiCheck:
    """
    Check to be performed on  a Mediawiki.
    """

    def __init__(self, name, func, checked=True):
        self.name = name
        self.func = func  # the check function to be performed on a WikiState
        self.checked = checked
        self.checkbox = None

    def as_checkbox(self):
        """
        Return a checkbox representation of the instance.
        """
        self.checkbox = ui.checkbox(self.name).bind_value(self, "checked")
        return self.checkbox


class WikiGrid:
    """
    A grid of Wikis.
    """

    def __init__(self, solution):
        # back reference to nicegui solution
        self.solution = solution

        self.wiki_users = WikiUser.getWikiUsers()
        self.wiki_clients = {}
        self.smw_clients = {}
        self.sorted_wiki_users = sorted(
            self.wiki_users.values(), key=lambda w: w.wikiId
        )
        self.lod = []
        self.wikistates_by_row_no = {}
        for index, wiki_user in enumerate(self.sorted_wiki_users):
            wiki_state = WikiState(index, wiki_user)
            record = wiki_state.as_dict()
            self.lod.append(record)
            self.wikistates_by_row_no[wiki_state.row_no] = wiki_state

    def setup(self):
        """
        setup the ui
        """
        self.add_checkboxes()
        self.progressbar = NiceguiProgressbar(
            len(self.wikistates_by_row_no), "work on wikis", "steps"
        )
        self.as_grid()
        self.lod_grid.update()

    def as_grid(self):
        # Configure grid with checkbox selection
        grid_config = GridConfig(
            key_col="#",
            editable=False,
            multiselect=True,
            with_buttons=True,
            button_names=["all", "fit"],
            debug=False,
        )
        self.lod_grid = ListOfDictsGrid(lod=self.lod,config=grid_config)
        self.lod_grid.ag_grid._props["html_columns"] = [0, 1, 2]
        return self.lod_grid

    def add_checkboxes(self):
        """
        Add check boxes.
        """
        self.button_row=ui.row()
        with self.button_row:
            self.wiki_checks = [
                WikiCheck("version", self.check_wiki_version),
                WikiCheck("backup", self.check_backup),
                WikiCheck("pages", self.check_pages),
            ]
            for wiki_check in self.wiki_checks:
                wiki_check.as_checkbox()
            ui.button(text="Checks", on_click=self.perform_wiki_checks)

    async def get_selected_lod(self):
        lod_index=self.lod_grid.get_index(lenient=self.lod_grid.config.lenient,lod=self.lod)
        lod = await self.lod_grid.get_selected_lod(lod_index=lod_index)
        if len(lod)==0:
            with self.button_row:
                ui.notify("Please select at least one row")
        return lod

    async def perform_wiki_checks(self, _msg):
        """
        react on the button for check having been clicked
        """
        self.select_lod=await self.get_selected_lod()
        if self.select_lod:
            with self.solution.content_div:
                total=len(self.select_lod)
                ui.notify(f"Checking {total} wikis ...")
                progress_bar = self.progressbar
                steps=0
                for wiki_check in self.wiki_checks:
                    if wiki_check.checked:
                        steps+=total
                progress_bar.total=steps
                progress_bar.reset()
                for row in self.select_lod:
                    row_no=row["#"]
                    wiki_state=self.wikistates_by_row_no.get(row_no)
                    wiki_state.task_runner.run(lambda: self.run_wiki_check(row_no))

    async def run_wiki_check(self,row_no:int):
        """
        perform the selected wiki checks
        """
        try:
            wiki_state=self.wikistates_by_row_no.get(row_no)
            for wiki_check in self.wiki_checks:
                if wiki_check.checked:
                    wiki_check.func(wiki_state)
                with self.solution.content_div:
                    self.lod_grid.update()
                    # Update the progress bar
                    self.progressbar.update(1)
        except BaseException as ex:
            self.solution.handle_exception(ex)

    def check_pages(self, wiki_state):
        """
        Try login for wiki user and report success or failure.
        """
        try:
            try:
                client=wiki_state.wiki_client
                if client.needs_login:
                    client.login()
                stats = wiki_state.wiki_client.get_site_statistics()
                pages = stats["pages"]
                self.lod_grid.update_cell(wiki_state.row_no, "login", f"✅")
                self.lod_grid.update_cell(wiki_state.row_no, "pages", f"✅{pages}")
            except Exception as ex:
                self.lod_grid.update_cell(wiki_state.row_no, "login", f"❌ {str(ex)}")
                self.lod_grid.update_cell(wiki_state.row_no, "pages", "❌")
                return
        except BaseException as ex:
            self.solution.handle_exception(ex)

    def check_wiki_version(self, wiki_state):
        """
        Check the MediaWiki version for a specific WikiState.
        """
        try:
            wiki_url = wiki_state.wiki_user.getWikiUrl()
            if not "index.php" in wiki_url:
                wiki_url=f"{wiki_url}/index.php"
            mw_site=MediaWikiSite(wiki_url)
            mw_version = mw_site.check_version()
            if not mw_version.startswith("MediaWiki"):
                mw_version = f"MediaWiki {mw_version}"
            row = self.lod_grid.get_row_for_key(wiki_state.row_no)
            if row:
                ex_version = wiki_state.wiki_user.version
                if ex_version == mw_version:
                    self.lod_grid.update_cell(
                        wiki_state.row_no, "version", f"{mw_version}✅"
                    )
                else:
                    self.lod_grid.update_cell(
                        wiki_state.row_no, "version", f"{ex_version}!={mw_version}❌"
                    )
        except BaseException as ex:
            self.solution.handle_exception(ex)

    def check_backup(self, wiki_state):
        """
        Check the backup status for a specific WikiUser.
        """
        try:
            row = self.lod_grid.get_row_for_key(wiki_state.row_no)
            if row:
                backup_path = f"{Path.home()}/wikibackup/{wiki_state.wiki_user.wikiId}"
                if os.path.isdir(backup_path):
                    wiki_files = glob.glob(f"{backup_path}/*.wiki")
                    msg = f"{len(wiki_files):6} ✅"
                    self.lod_grid.update_cell(wiki_state.row_no, "backup", msg)
                    # https://stackoverflow.com/a/39327156/1497139
                    if wiki_files:
                        latest_file = max(wiki_files, key=os.path.getctime)
                        st = os.stat(latest_file)
                        age_days = round((time.time() - st.st_mtime) / 86400)
                        self.lod_grid.update_cell(
                            wiki_state.row_no, "age", f"{age_days}"
                        )
                else:
                    msg = "❌"
                    self.lod_grid.update_cell(wiki_state.row_no, "backup", msg)
        except BaseException as ex:
            self.solution.handle_exception(ex)
