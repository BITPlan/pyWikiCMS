"""
Created on 2021-01-01

@author: wf
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from wikibot3rd.wikipush import WikiPush
from wikibot3rd.wikiuser import WikiUser

from backend.remote import Remote


class WikiBackup:
    """
    WikiBackup handling for a WikiUser

    """

    def __init__(self, wikiuser: WikiUser, remote: Remote = None, debug: bool = False):
        """
        constructor

        Arguments:
            wikiuser(WikiUser): the wikiuser to access this backup
            remote(Remote): the remote access to use
        """
        self.wikiuser = wikiuser
        self._remote = remote
        self.debug = debug
        home = str(Path.home())
        self.wikibackup_path = f"{home}/wikibackup/{wikiuser.wikiId}"
        self.git_path = f"{self.wikibackup_path}/.git"
        pass

    @property
    def remote(self) -> Remote:
        if self._remote is None:
            self._remote = Remote("localhost")
        return self._remote

    def exists(self) -> bool:
        """
        check if this Backup exists

        Returns:
            bool: True if the self.backupPath directory exists
        """
        exists = os.path.isdir(self.wikibackup_path)
        return exists

    def has_git(self) -> bool:
        """
        check if this Backup has a local git repository

        Returns:
            bool: True if the self.gitPath directory exists
        """
        has_git = os.path.isdir(self.git_path)
        return has_git

    def show_age(self):
        """
        show the age of this backup
        """
        stats = self.remote.get_file_stats(self.wikibackup_path)
        age_days = stats.age_days
        print(f"{self.wikiuser.wikiId}: {age_days:.2f} days")

    def backup(
        self,
        days: int,
        query_division: int = 10,
        with_login: bool = True,
        with_git: bool = True,
        show_progress: bool = True,
        with_images: bool = True,
    ):
        """
        perform the backup
        """
        stats = self.remote.get_file_stats(self.wikibackup_path)
        if days < 0 or stats is None:
            query = "[[Modification date::+]]"
        else:
            cutoff = datetime.now() - timedelta(days=days)
            days_ago_iso = cutoff.strftime("%Y-%m-%d")
            query = f"[[Modification date::>{days_ago_iso}]]"

        wikipush = WikiPush(
            fromWikiId=self.wikiuser.wikiId,
            toWikiId=None,
            login=with_login,
            debug=self.debug,
        )

        pages = wikipush.query(
            query,
            wiki=None,  # selects fromWiki
            pageField=None,
            limit=None,
            showProgress=show_progress,
            queryDivision=query_division,
        )

        wikipush.backup(
            pages,
            git=with_git,
            withImages=with_images,
            backupPath=self.wikibackup_path,
        )
