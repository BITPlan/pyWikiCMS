'''
Created on 27.07.2020

@author: wf
'''
import unittest
import getpass
import os
from wikibot.wikiclient import WikiClient
from wikibot.wikiuser import WikiUser
#from wikibot.smw import SMWClient


class TestWikiCMS(unittest.TestCase):
    
    def setUp(self):
        self.debug=False
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
                wikiDict={"wikiId": wikiId,"email":"john@doe.com","url":"http://cr.bitplan.com","scriptPath":"/w","version":"MediaWiki 1.31.7"}
            elif wikiId=="smw":
                wikiDict={"wikiId": wikiId,"email":"john@doe.com","url":"https://www.semantic-mediawiki.org","scriptPath":"/w","version":"MediaWiki 1.31.7"}
            elif wikiId=="or":
                wikiDict={"wikiId": wikiId,"email":"john@doe.com","url":"https://www.openresearch.org","scriptPath":"/mediawiki/","version":"MediaWiki 1.31.1"}   
            if wikiDict is None:
                raise Exception("%s missing for wikiId %s" % (iniFile,wikiId))
            else:
                wikiUser=WikiUser.ofDict(wikiDict, lenient=True)
                user=getpass.getuser()
                print("user is: %s" % user)
                # check the continuous integration users
                if user=="travis" or user=="runner":
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
        wikiclient=TestWikiCMS.getSMW_Wiki("or")
        pageTitle="Main Page"
        page=wikiclient.getPage(pageTitle)
        text=page.text()
        if self.debug:
            print(text)
        self.assertTrue("OpenResearch" in text)
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()