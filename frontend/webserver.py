'''
Created on 27.07.2020

@author: wf
'''
from flask import Flask
from frontend.WikiCMS import Frontend
from flask import render_template
import os

class AppWrap:
    def __init__(self, host='0.0.0.0',port=8251,debug=False):
        self.debug=debug
        self.port=port
        self.host=host    
        scriptdir=os.path.dirname(os.path.abspath(__file__))
        self.app = Flask(__name__,template_folder=scriptdir+'/../templates')
        self.frontend=None
        
    def wrap(self,route):
        if self.frontend is None:
            raise Exception("frontend is not initialized")
        content,error=self.frontend.getContent(route);
        return render_template('index.html',content=content,error=error)
        
    def run(self):
        self.app.run(debug=self.debug,port=self.port,host=self.host)   
        pass

    def initFrontend(self,wikiId):
        self.frontend=Frontend(wikiId)
        self.frontend.open()
    
appWrap=AppWrap()
app=appWrap.app    
@app.route('/', defaults={'path': ''})
@app.route('/<path:route>')
def wrap(route):
    return appWrap.wrap(route)

if __name__ == '__main__':
    appWrap.run()
    