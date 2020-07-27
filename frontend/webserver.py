'''
Created on 27.07.2020

@author: wf
'''
from flask import Flask
from frontend.WikiCMS import Frontend
from flask import render_template
import os
debug=False
port=8251
host='0.0.0.0'
scriptdir=os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,template_folder=scriptdir+'/../templates')
frontend=Frontend("cr")

@app.route('/', defaults={'path': ''})
@app.route('/<path:route>')
def wrap(route):
    content,error=frontend.getContent(route);
    return render_template('index.html',content=content,error=error)

if __name__ == '__main__':
    app.run(debug=debug,port=port,host=host)   