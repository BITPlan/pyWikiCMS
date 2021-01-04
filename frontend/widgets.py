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
    def __init__(self,url,alt=None):
        self.url=url
        if alt is not None:
            self.alt=alt
        else:
            self.alt=url
        
    def render(self):
        '''
        render me
        
        Returns:
            str: html code for Image
        '''
        html="<img src='%s' alt='%s'/>" % (self.url,self.alt)
        return html