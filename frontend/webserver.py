'''
Created on 27.07.2020

@author: wf
'''
from flask import Flask
from frontend.WikiCMS import Frontend
from flask import render_template
from pydevd_file_utils import setup_client_server_paths
import argparse
import os

class AppWrap:
    ''' Wrapper for Flask Web Application 
    '''
    
    def __init__(self, host='0.0.0.0',port=8251,debug=False):
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
        scriptdir=os.path.dirname(os.path.abspath(__file__))
        self.app = Flask(__name__,template_folder=scriptdir+'/../templates')
        self.frontends={}
        self.enabledSites=[]
    
    def enableSites(self,sites):
        '''
        enable the sites given in the sites list
        Args:
            sites(list): a list of strings with wikiIds to be enabled
        '''
        self.enabledSites.extend(sites)
        
    def wrap(self,site,path):
        '''
        wrap the given path for the given site
        Args:
            site(str): the site to wrap
            path(path): the path to wrap
        '''
        content=None
        if not site in self.enabledSites:
            error="access to site %s is not enabled you might want to add it via the --sites command line option" % site
        else:
            if not site in self.frontends:
                self.frontends[site]=Frontend(site)
            
            frontend=self.frontends[site]     
            frontend.open()     
            content,error=frontend.getContent(path);
        return render_template('index.html',content=content,error=error)
       
    def run(self):
        '''
        start the flask webserver
        '''
        self.app.run(debug=self.debug,port=self.port,host=self.host)   
        pass
    
appWrap=AppWrap()
app=appWrap.app   
@app.route('/', defaults={'path': ''})
@app.route('/<path:site>/<path:path>')
def wrap(site,path):
    return appWrap.wrap(site,path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Wiki Content Management webservice")
    parser.add_argument('--debug',
                                 action='store_true',
                                 help="run in debug mode")
    parser.add_argument('--debugServer',
                                 help="remote debug Server")
    parser.add_argument('--debugPort',type=int,
                                 help="remote debug Port",default=5678)
    parser.add_argument('--debugPathMapping',nargs='+',help="remote debug Server path mapping - needs two arguments 1st: remotePath 2nd: local Path")
    parser.add_argument('--sites',nargs='+',required=True,help="the sites to enable")
    args=parser.parse_args()
    if args.debugServer:
        import pydevd
        print (args.debugPathMapping,flush=True)
        if args.debugPathMapping:
            if len(args.debugPathMapping)==2:
                remotePath=args.debugPathMapping[0] # path on the remote debugger side
                localPath=args.debugPathMapping[1]  # path on the local machine where the code runs
                MY_PATHS_FROM_ECLIPSE_TO_PYTHON = [
                    (remotePath, localPath),
                ]
                setup_client_server_paths(MY_PATHS_FROM_ECLIPSE_TO_PYTHON)
                #os.environ["PATHS_FROM_ECLIPSE_TO_PYTHON"]='[["%s", "%s"]]' % (remotePath,localPath)
                #print("trying to debug with PATHS_FROM_ECLIPSE_TO_PYTHON=%s" % os.environ["PATHS_FROM_ECLIPSE_TO_PYTHON"]);
     
        pydevd.settrace(args.debugServer, port=args.debugPort,stdoutToServer=True, stderrToServer=True)
    appWrap.debug=args.debug
    appWrap.enableSites(args.sites)
    appWrap.run()
    