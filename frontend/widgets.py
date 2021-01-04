'''
Created on 2021-01-04

@author: wf
'''
class Widget(object):
    def __init(self):
        pass
    
    def __str__(self):
        html=self.render()
        return html

class Link(Widget):   
    '''
    a HTML link
    '''
    def __init__(self,url,title,tooltip=None):
        self.url=url
        self.title=title
        self.tooltip=tooltip
        
    def render(self):
        html="<a href='%s'>%s</a>" % (self.url,self.title)
        return html
        
class Image(Widget):
    '''
    a HTML Image
    '''
    def __init__(self,url):
        self.url=url
        
    def render(self):
        html="<img src='%s'/>" % (self.url)
        return html