'''
Created on 27.07.2020

@author: wf
'''
import unittest
import os
from wikibot.wikibot import WikiBot

class TestWikiCMS(unittest.TestCase):

    @staticmethod
    def getSMW_Wiki(wikiId="cr"):
        iniFile=WikiBot.iniFilePath(wikiId)
        if not os.path.isfile(iniFile):
            if wikiId=="smw":
                WikiBot.writeIni(wikiId,"Semantic MediaWiki","https://www.semantic-mediawiki.org","/w","MediaWiki 1.31.7")
            if wikiId=="or":
                WikiBot.writeIni(wikiId,"OpenResearch.org","https://www.openresearch.org","/mediawiki/","MediaWiki 1.31.1")    
            if wikiId=="cr":
                WikiBot.writeIni(wikiId,"Conference Lookup","http://cr.bitplan.com","/","MediaWiki 1.33.2")    
        wikibot=WikiBot.ofWikiId(wikiId)
        return  wikibot
    
    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testWikiCMS(self):
        ''' test CMS access '''
        wikibot=TestWikiCMS.getSMW_Wiki("or")
        pageTitle="Main Page"
        page=wikibot.getPage(pageTitle)
        # print(page.text)
        self.assertTrue("OpenResearch" in page.text)
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()