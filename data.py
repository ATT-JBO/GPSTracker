__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

class Credentials():
    def __init__(self):
        self.userName = ''
        self.password = ''
        self.server = ''
        self.broker = ''
        self.groundid = ''


credentials = Credentials()
credentials.userName = "sander"
credentials.password = "attsander"
credentials.broker = "tasty.allthingstalk.io"
credentials.server = "tasty.allthingstalk.io"
credentials.groundid =  "92SkKNHz2eaIqgJUnC15AdIv"