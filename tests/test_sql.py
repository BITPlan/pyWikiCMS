'''
Created on 2021-01-10

@author: wf
'''
import unittest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from frontend.server import Server
from tests.basetest import Basetest

class TestSQL(Basetest):
    '''
    test SQL access
    '''

    def setUp(self):
        Basetest.setUp(self)
        pass


    def testSQL(self):
        '''
        try out SQL access with SQL Alchemy
        '''
        server=Server()
        server.load()
        app = Flask(__name__)
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
  
        if "credentials" in server.__dict__:
            server.hostname="capri.bitplan.com"
            cred=server.credentials[0]
            user=cred["user"]
            password=cred["password"]
            dbname=cred["dbname"]
            dburl=server.sqlGetDatabaseUrl(dbname,user,password)
            
            dbExists=server.sqlDatabaseExist(dburl)
            self.assertTrue(dbExists)
            app.config["SQLALCHEMY_DATABASE_URI"] = dburl
            sqldb = SQLAlchemy(app)
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()