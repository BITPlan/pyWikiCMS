'''
Created on 2020-07-27

@author: wf
'''

from pydevd_file_utils import setup_client_server_paths
import argparse
from frontend.app import AppWrap
    
appWrap=AppWrap()
app=appWrap.app   
@app.route('/')
def admin():
    return appWrap.admin()

@app.route('/wikis')
def wikis():
    return appWrap.wikis()
    
@app.route('/<path:path>')
def wrap(path):
    '''
    wrap the url request for the given path
    
    Args:
        path(str): the path to wrap - the path should start with /<wikiId>/ followed by the actual path in the wiki
    '''
    site,path=AppWrap.splitPath(path)
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
    