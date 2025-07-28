"""
Created on 2022-12-03

@author: wf
"""

import glob
import os
import time
from pathlib import Path

from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.progress import NiceguiProgressbar
from ngwidgets.task_runner import TaskRunner
from nicegui import ui

from backend.site import WikiSite, Wikis


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

    def __init__(self, solution, wikis: Wikis):
        # back reference to nicegui solution
        self.solution = solution
        self.wikis = wikis
        self.task_runner = TaskRunner(timeout=40)

    def setup(self):
        """
        setup the ui
        """
        self.add_checkboxes()
        self.progressbar = NiceguiProgressbar(
            self.wikis.get_wiki_count(), "work on wikis", "steps"
        )
        self.task_runner.progress = self.progressbar
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
        self.lod_grid = ListOfDictsGrid(lod=self.wikis.get_lod(), config=grid_config)
        self.lod_grid.ag_grid._props["html_columns"] = [0, 1, 2]
        return self.lod_grid

    def add_checkboxes(self):
        """
        Add check boxes.
        """
        self.button_row = ui.row()
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
        lod_index = self.lod_grid.get_index(
            lenient=self.lod_grid.config.lenient, lod=self.wikis.get_lod()
        )
        lod = await self.lod_grid.get_selected_lod(lod_index=lod_index)
        if len(lod) == 0:
            with self.button_row:
                ui.notify("Please select at least one row")
        return lod

    async def perform_wiki_checks(self, _msg):
        """
        react on the button for check having been clicked
        """
        self.select_lod = await self.get_selected_lod()
        if self.select_lod:
            with self.solution.content_div:
                total = len(self.select_lod)
                ui.notify(f"Checking {total} wikis ...")
                # Use single task_runner
                self.task_runner.run_blocking(self.run_all_wiki_checks)

    def run_all_wiki_checks(self):
        """
        Process all selected wikis sequentially
        """
        try:
            # Calculate total steps
            steps = 0
            for wiki_check in self.wiki_checks:
                if wiki_check.checked:
                    steps += len(self.select_lod)
            self.progressbar.total = steps
            self.progressbar.reset()

            # Process each wiki sequentially
            for row in self.select_lod:
                row_no = row["#"]
                wikisite = self.wikis.get_wikisite_by_row(row_no)
                self.run_wiki_check(wikisite)

        except BaseException as ex:
            self.solution.handle_exception(ex)

    def run_wiki_check(self, wiki_state):
        """
        perform the selected wiki checks for a single wiki
        """
        try:
            for wiki_check in self.wiki_checks:
                if wiki_check.checked:
                    wiki_check.func(wiki_state)
                with self.solution.content_div:
                    self.lod_grid.update()
                    # Update the progress bar
                    self.progressbar.update(1)
        except BaseException as ex:
            self.solution.handle_exception(ex)

    def check_pages(self, wiki_state: WikiSite):
        """
        Try login for wiki user and report success or failure.
        """
        try:
            try:
                client = wiki_state.wiki_client
                stats = client.get_site_statistics()
                pages = stats["pages"]
                self.lod_grid.update_cell(wiki_state.row_no, "login", f"✅")
                self.lod_grid.update_cell(wiki_state.row_no, "pages", f"✅{pages}")
            except Exception as ex:
                self.lod_grid.update_cell(wiki_state.row_no, "login", f"❌ {str(ex)}")
                self.lod_grid.update_cell(wiki_state.row_no, "pages", "❌")
                return
        except BaseException as ex:
            self.solution.handle_exception(ex)

    def check_wiki_version(self, wiki_state: WikiSite):
        """
        Check the MediaWiki version for a specific WikiState.
        """
        try:
            mw_version = wiki_state.check_version()
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
