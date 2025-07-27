"""
Created on 2021-01-01

@author: wf
"""

import os
from pathlib import Path


class WikiBackup(object):
    """
    find out details about a WikiBackup

    potentially this class needs to move upstream to py-3rdparty-MediaWiki
    """

    def __init__(self, wikiuser):
        """
        constructor

        Arguments:
            wikiuser(WikiUser): the wikiuser to access this backup
        """
        self.wikiuser = wikiuser
        home = str(Path.home())
        self.backupPath = f"{home}/wikibackup/{wikiuser.wikiId}"
        self.gitPath = f"{self.backupPath}/.git"
        pass

    def exists(self) -> bool:
        """
        check if this Backup exists

        Returns:
            bool: True if the self.backupPath directory exists
        """
        return os.path.isdir(self.backupPath)

    def hasGit(self) -> bool:
        """
        check if this Backup has a local git repository

        Returns:
            bool: True if the self.gitPath directory exists
        """
        return os.path.isdir(self.gitPath)
