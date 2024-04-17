"""
Created on 2022-12-03

@author: wf
"""
import glob
import os
import time
from pathlib import Path

from lodstorage.lod import LOD
from ngwidgets.lod_grid import ListOfDictsGrid
from ngwidgets.progress import NiceguiProgressbar, Progressbar
from ngwidgets.widgets import Link
from nicegui import ui, run
from wikibot3rd.smw import SMWClient
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.wikiuser import WikiUser

from frontend.family import WikiBackup, WikiFamily
from frontend.html_table import HtmlTables


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
        }
        return record


class WikiCheck:
    """
    A check for a Mediawiki.
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
        self.add_checkboxes()
        self.progressbar = NiceguiProgressbar(
            len(self.wikistates_by_row_no), "work on wikis", "steps"
        )
        self.as_grid()
        self.lod_grid.update()

    def as_grid(self):
        self.lod_grid = ListOfDictsGrid(lod=self.lod)
        self.lod_grid.ag_grid._props["html_columns"] = [0, 1, 2]
        return self.lod_grid

    def add_checkboxes(self):
        """
        Add check boxes.
        """
        self.wiki_checks = [
            WikiCheck("version", self.check_wiki_version),
            WikiCheck("backup", self.check_backup),
            WikiCheck("pages", self.check_pages),
        ]
        for wiki_check in self.wiki_checks:
            wiki_check.as_checkbox()
        ui.button(text="Checks", on_click=self.perform_wiki_checks)

    def check_version(self, wiki_url):
        """
        Check the MediaWiki version.
        """
        version_url = f"{wiki_url}/index.php/Special:Version"
        mw_version = "?"
        try:
            html_tables = HtmlTables(version_url)
            tables = html_tables.get_tables("h2")
            if "Installed software" in tables:
                software = tables["Installed software"]
                software_map, _dup = LOD.getLookup(
                    software, "Product", withDuplicates=False
                )
                mw_version = software_map["MediaWiki"]["Version"]
        except Exception as ex:
            mw_version = f"error: {str(ex)}"
        return mw_version

    async def perform_wiki_checks(self, _msg):
        await run.io_bound(self.run_wiki_checks)

    def run_wiki_checks(self, progress_bar: Progressbar = None):
        """
        perform the selected wiki checks
        """
        try:
            progress_bar.reset()
            for wiki_state in self.wikistates_by_row_no.values():
                for wiki_check in self.wiki_checks:
                    if wiki_check.checked:
                        wiki_check.func(wiki_state)
                self.lod_grid.update()
                if progress_bar:
                    # Update the progress bar
                    progress_bar.update(1)
        except BaseException as ex:
            self.solution.handle_exception(ex)

    def check_pages(self, wiki_state):
        """
        Try login for wiki user and report success or failure.
        """
        try:
            wiki_state.wiki_client = WikiClient.ofWikiUser(wiki_state.wiki_user)
            try:
                wiki_state.wiki_client.login()
                stats = wiki_state.wiki_client.get_site_statistics()
                pages = stats["pages"]
                self.lod_grid.update_row(wiki_state.row_no, "login", f"✅")
                self.lod_grid.update_row(wiki_state.row_no, "pages", f"✅{pages}")
            except Exception as ex:
                self.lod_grid.update_row(wiki_state.row_no, "login", f"❌ {str(ex)}")
                self.lod_grid.update_row(wiki_state.row_no, "pages", "❌")
                return
        except BaseException as ex:
            self.solution.handle_exception(ex)

    def check_wiki_version(self, wiki_state):
        """
        Check the MediaWiki version for a specific WikiState.
        """
        try:
            wiki_url = wiki_state.wiki_user.getWikiUrl()
            mw_version = self.check_version(wiki_url)
            if not mw_version.startswith("MediaWiki"):
                mw_version = f"MediaWiki {mw_version}"
            row = self.lod_grid.get_row_for_key(wiki_state.row_no)
            if row:
                ex_version = row["version"]
                if ex_version == mw_version:
                    self.lod_grid.update_row(
                        wiki_state.row_no, "version", f"{mw_version}✅"
                    )
                else:
                    self.lod_grid.update_row(
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
                    self.lod_grid.update_row(wiki_state.row_no, "backup", msg)
                    # https://stackoverflow.com/a/39327156/1497139
                    if wiki_files:
                        latest_file = max(wiki_files, key=os.path.getctime)
                        st = os.stat(latest_file)
                        age_days = round((time.time() - st.st_mtime) / 86400)
                        self.lod_grid.update_row(
                            wiki_state.row_no, "age", f"{age_days}"
                        )
                else:
                    msg = "❌"
                    self.lod_grid.update_row(wiki_state.row_no, "backup", msg)
        except BaseException as ex:
            self.solution.handle_exception(ex)
