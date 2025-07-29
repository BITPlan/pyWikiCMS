"""
Created on 2021-01-01

@author: wf
"""

from datetime import datetime, timedelta
import os
from pathlib import Path

from backend.remote import Remote
from wikibot3rd.wikipush import WikiPush
from wikibot3rd.wikiuser import WikiUser


class WikiBackup():
    """
    WikiBackup handling for a WikiUser

    """
    def __init__(self, wikiuser: WikiUser, remote:Remote=None,debug: bool = False):
        """
        constructor

        Arguments:
            wikiuser(WikiUser): the wikiuser to access this backup
            remote(Remote): the remote access to use
        """
        self.wikiuser = wikiuser
        self.remote=remote
        self.debug = debug
        home = str(Path.home())
        self.wikibackup_path = f"{home}/wikibackup/{wikiuser.wikiId}"
        self.git_path = f"{self.wikibackup_path}/.git"
        pass

    def exists(self) -> bool:
        """
        check if this Backup exists

        Returns:
            bool: True if the self.backupPath directory exists
        """
        exists=os.path.isdir(self.wikibackup_path)
        return exists

    def has_git(self) -> bool:
        """
        check if this Backup has a local git repository

        Returns:
            bool: True if the self.gitPath directory exists
        """
        has_git= os.path.isdir(self.git_path)
        return has_git

    def show_age(self):
        stats=self.remote.get_file_stats(self.wikibackup_path)
        age_days=stats.age_days
        print(f"{self.wikiuser.wikiId}: {age_days} days")

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
        if days < 0:
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
