'''
Created on 27.07.2020

@author: wf
'''
from flask import Flask
from frontend.WikiCMS import Frontend
from flask import render_template
import argparse
import os

class AppWrap:
    ''' Wrapper for Flask Web Application 
    '''
    
    def __init__(self, wikiId='cr',host='0.0.0.0',port=8251,debug=False):
        '''
        constructor
        
        Args:
            wikiId(str): id of the wiki to use as a CMS backend
            host(str): flask host
            port(int): the port to use for http connections
            debug(bool): True if debugging should be switched on
        '''
        self.debug=debug
        self.port=port
        self.host=host    
        self.wikiId=wikiId
        scriptdir=os.path.dirname(os.path.abspath(__file__))
        self.app = Flask(__name__,template_folder=scriptdir+'/../templates')
        self.frontend=None
        
    def wrap(self,route):
        '''
        wrap the given route 
        '''
        if self.frontend is None:
            self.initFrontend(self.wikiId)
        content,error=self.frontend.getContent(route);
        return render_template('index.html',content=content,error=error)

    def initFrontend(self,wikiId):
        '''
        initialize the frontend for the given wikiId
        '''
        self.frontend=Frontend(wikiId)
        self.frontend.open()
        
    def run(self):
        '''
        start the flask webserver
        '''
        self.app.run(debug=self.debug,port=self.port,host=self.host)   
        pass
    
appWrap=AppWrap()
app=appWrap.app   
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def wrap(path):
    return appWrap.wrap(path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Wiki Content Management webservice")
    parser.add_argument('--debug',
                                 action='store_true',
                                 help="run in debug mode")
    parser.add_argument('--debugServer',
                                 help="remote debug Server")
    parser.add_argument('--debugPathMapping',nargs='+',help="remote debug Server path mapping - needs two arguments 1st: remotePath 2nd: local Path")
    parser.add_argument('--debugPort',type=int,
                                 help="remote debug Port",default=5678)
    args=parser.parse_args()
    if args.debugServer:
        import pydevd
        print (args.debugPathMapping,flush=True)
        if args.debugPathMapping:
            if len(args.debugPathMapping)==2:
                remotePath=args.debugPathMapping[0]
                localPath=args.debugPathMapping[1]
                os.environ["PATHS_FROM_ECLIPSE_TO_PYTHON"]='[["%s", "%s"]]' % (remotePath,localPath)
                print("trying to debug with PATHS_FROM_ECLIPSE_TO_PYTHON=%s" % os.environ["PATHS_FROM_ECLIPSE_TO_PYTHON"]);
     
        pydevd.settrace(args.debugServer, port=args.debugPort,stdoutToServer=True, stderrToServer=True)
    appWrap.debug=args.debug
    appWrap.run()
    