'''
Created on 27.07.2020

@author: wf
'''
import unittest
import os
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.wikiuser import WikiUser
#from wikibot.smw import SMWClient
from tests.basetest import Basetest

class TestWikiCMS(Basetest):
    '''
    test the Mediawiki based Content Management System
    '''
    
    def setUp(self):
        Basetest.setUp(self)
        pass


    def tearDown(self):
        pass
    
    @staticmethod
    def getSMW_WikiUser(wikiId="cr"):
        '''
        get semantic media wiki users for SemanticMediawiki.org and openresearch.org
        '''
        iniFile=WikiUser.iniFilePath(wikiId)
        wikiUser=None
        if not os.path.isfile(iniFile):
            wikiDict=None
            if wikiId=="smwcopy":
                wikiDict={"wikiId": wikiId,"email":"john@doe.com","url":"http://smw.bitplan.com","scriptPath":"","version":"MediaWiki 1.35.0"}
            elif wikiId=="cr":
                wikiDict={"wikiId": wikiId,"email":"john@doe.com","url":"http://cr.bitplan.com","scriptPath":"","version":"MediaWiki 1.33.4"}
            elif wikiId=="smw":
                wikiDict={"wikiId": wikiId,"email":"john@doe.com","url":"https://www.semantic-mediawiki.org","scriptPath":"/w","version":"MediaWiki 1.31.7"}
            elif wikiId=="or":
                wikiDict={"wikiId": wikiId,"email":"john@doe.com","url":"https://www.openresearch.org","scriptPath":"/mediawiki/","version":"MediaWiki 1.31.1"}  
            elif wikiId=="orclone":
                wikiDict={"wikiId": wikiId,"email":"noreply@nouser.com","url":"https://confident.dbis.rwth-aachen.de","scriptPath":"/or/","version":"MediaWiki 1.35.1"}
         
            elif wikiId=='wiki':
                wikiDict={"wikiId": wikiId,"email":"john@doe.com","url":"https://wiki.bitplan.com","scriptPath":"","version":"MediaWiki 1.27.3"}                       
            if wikiDict is None:
                raise Exception(f"{iniFile} missing for wikiId {wikiId}")
            else:
                wikiUser=WikiUser.ofDict(wikiDict, lenient=True)
                if Basetest.inPublicCI():
                    wikiUser.save()
        else: 
            wikiUser=WikiUser.ofWikiId(wikiId,lenient=True)
        return wikiUser


    @staticmethod
    def getSMW_Wiki(wikiId="cr"):
        wikiuser=TestWikiCMS.getSMW_WikiUser(wikiId)
        wikiclient=WikiClient.ofWikiUser(wikiuser)
        return wikiclient

    def testWikiCMS(self):
        ''' test CMS access '''
        wikiclient=TestWikiCMS.getSMW_Wiki("orclone")
        pageTitle="Main Page"
        page=wikiclient.getPage(pageTitle)
        text=page.text()
        if self.debug:
            print(text)
        self.assertTrue("OpenResearch" in text)
        pass