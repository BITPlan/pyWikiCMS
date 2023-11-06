"""
Created on 2023-11-06

@author: wf
"""
import os
from ngwidgets.basetest import Basetest
from frontend.clickstream import ClickstreamManager

class TestClickstreams(Basetest):
    """
    test clickstream log reading
    """
    
    def testReadingLogs(self):
        """
        test reading click stream logs
        """
        home_directory = os.path.expanduser("~")  # Get the home directory path
        root_path = os.path.join(home_directory, '.clickstream')  # Set the root path to $HOME/.clickstream
        if os.path.isdir(root_path):
            manager = ClickstreamManager(root_path)
            limit=20
            manager.load_clickstream_logs(limit=limit)
            self.assertEqual(limit,len(manager.clickstream_logs))