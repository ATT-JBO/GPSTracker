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


credentials = Credentials()
credentials.userName = "Geotrigger"
credentials.password = "Att953953"
credentials.broker = "broker.smartliving.io"
credentials.server = "api.smartliving.io"