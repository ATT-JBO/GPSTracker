__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import kivy
kivy.require('1.9.1')   # replace with your current kivy version !

import logging
logging.getLogger().setLevel(logging.INFO)

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.utils import platform
from kivy.lib import osc


from ConfigParser import *

import attiotuserclient as IOT
from errors import *
import data


appConfigFileName = 'app.config'
IPCPort = 3000
IPCServicePort = 3001


class CredentialsDialog(Popup):
    "set credentials"
    userNameInput = ObjectProperty()
    pwdInput = ObjectProperty()

    serverInput = ObjectProperty()
    brokerInput = ObjectProperty()

    def __init__(self, credentials, callback, **kwargs):
        self.callback = callback
        super(CredentialsDialog, self).__init__(**kwargs)
        if credentials:
            self.userNameInput.text = credentials.userName
            self.pwdInput.text = credentials.password
            if hasattr(credentials, 'server') and credentials.server:
                self.serverInput.text = credentials.server
            else:
                self.serverInput.text = 'api.smartliving.io'
            if hasattr(credentials, 'broker') and credentials.broker:
                self.brokerInput.text = credentials.broker
            else:
                self.brokerInput.text = 'broker.smartliving.io'
        else:
            self.serverInput.text = 'api.smartliving.io'
            self.brokerInput.text = 'broker.smartliving.io'

    def dismissOk(self):
        if self.callback:
            credentials = Credentials()
            credentials.userName = self.userNameInput.text
            credentials.password = self.pwdInput.text
            credentials.server = self.serverInput.text
            credentials.broker = self.brokerInput.text
            self.callback(credentials)
        self.dismiss()

def getRunningService():
    '''check if service is running '''
    from plyer.platforms.android import activity
    from jnius import autoclass
    import sys
    Context = autoclass('android.content.Context')
    manager = activity.getSystemService(Context.ACTIVITY_SERVICE)
    for myService in manager.getRunningServices(sys.maxint).toArray():
        if str(myService.service.flattenToString()) == "gpstracker.org.test.gpstracker/org.renpy.android.PythonService":
            return myService
    return None

def connect():
    try:
        IOT.connect(data.credentials.userName, data.credentials.password,data.credentials.server, data.credentials.broker)
        logging.info("connected")
    except Exception as e:
        showError(e)

def IPCCallback(message, *args):
    logging.info('got message: %s' % message)

class MainWindow(Widget):
    destination = StringProperty('Unknown')
    selectedDeviceName = StringProperty('Select device')
    isRunning = BooleanProperty(False)

    def __init__(self, **kwargs):
        if platform == 'android':
            self.service = getRunningService()
            self.isRunning = self.service != None
        else:
            self.service = None
            self.isRunning = False
        super(MainWindow, self).__init__(**kwargs)

    def getSettings(self):
        self.config = ConfigParser()
        if self.config.read(appConfigFileName):
            if self.config.has_option('general', 'device'):
                self.device = self.config.get('general', 'device')
            else:
                self.device = None
            if self.config.has_option('general', 'asset'):
                self.asset = self.config.get('general', 'asset')
            else:
                self.asset = None

            if self.config.has_option('general', 'userName'):
                data.credentials.userName = self.config.get('general', 'userName')
            else:
                data.credentials.userName = "Geotrigger"
            if self.config.has_option('general', 'password'):
                data.credentials.password = self.config.get('general', 'password')
            else:
                data.credentials.password = "Att953953"
            if self.config.has_option('general', 'server'):
                data.credentials.server = self.config.get('general', 'server')
            else:
                data.credentials.server = "api.smartliving.io"
            if self.config.has_option('general', 'broker'):
                data.credentials.broker = self.config.get('general', 'broker')
            else:
                data.credentials.broker = "broker.smartliving.io"

        else:
            self.device = None
            self.asset = None

    def updateDevName(self):
        if self.device:
            dev = IOT.getDevice(self.device)
            if dev:
                if 'title' in dev and dev['title']:
                    self.selectedDeviceName = dev['title']
                else:
                    self.selectedDeviceName = dev['name']

    def saveConfig(self):
        if not self.config.has_section('general'):
            self.config.add_section('general')
        self.config.set('general', 'device', self.device)
        self.config.set('general', 'asset', self.asset)
        self.config.set('general', 'userName', data.credentials.userName)
        self.config.set('general', 'password', data.credentials.password)
        self.config.set('general', 'server', data.credentials.server)
        self.config.set('general', 'broker', data.credentials.broker)
        with open(appConfigFileName, 'w') as f:
            self.config.write(f)

    def showSelectDevice(self, relativeTo):
        grounds = IOT.getGrounds(False)

        dropdown = DropDown() # auto_width=False, width='140dp'
        for ground in grounds:
            devices = IOT.getDevices(ground['id'])
            for dev in devices:
                btn = Button(size_hint_y=None, height='32dp')
                btn.DeviceId = dev['id']
                if dev['title']:
                    btn.text=dev['title']             # for old devices that didn't ahve a title yet.
                else:
                    btn.text=dev['name']
                btn.bind(on_release=lambda btn: self.selectDevice(btn.parent.parent, btn.DeviceId, btn.text))
                dropdown.add_widget(btn)
        dropdown.open(relativeTo)

    def showCredentialsDlg(self):
        dlg = CredentialsDialog(data.credentials, self.credentialsChanged)
        dlg.open()

    def credentialsChanged(self, newCredentials):
        IOT.disconnect(False)
        data.credentials = newCredentials
        connect()
        self.updateDevName()
        self.saveConfig()

    def selectDevice(self, dropdown, deviceId, title):
        if dropdown:
            dropdown.dismiss()
        self.selectedDeviceName = title
        self.device = deviceId
        if self.asset:
            IOT.unsubscribe(self.asset)
        self.asset = None
        if self.device:
            assets = IOT.getAssets(self.device)
            locationAsset = [asset for asset in assets if str(asset['name']).startswith('Destination') ]
            if locationAsset and len(locationAsset) > 0:
                self.asset = str(locationAsset[0]['id'])
                IOT.subscribe(self.asset, self.destinationChanged)
        if self.isRunning and platform == 'android':
            osc.sendMsg('/device', [str(self.device)], port=IPCServicePort)
        self.saveConfig()

    def destinationChanged(self, value):
        if value:
            self.destination = str(value)
        else:
            self.destination = 'Unknown'


    def startService(self, level):
        self.isRunning = True
        if platform == 'android':
            from android import AndroidService
            if not self.service:
                self.service = AndroidService('my gps service', 'running')
            if self.device:
                self.service.start(level + '|' + self.device + '|' + data.credentials.userName + '|' + IOT._brokerPwd)
            else:
                self.service.start(level)

    def stopService(self):
        if self.isRunning:
            if self.service:
                osc.sendMsg('/stop', [''], port=IPCServicePort)
                try:
                    self.service.stop()
                except Exception as e:
                    logging.exception('failed to stop service (need to do activity.stopService()')

        self.isRunning = False


class GpsTrackerApp(App):
    def build(self):
        osc.init()
        res = MainWindow()
        res.getSettings()
        if data.credentials.userName and data.credentials.password:
            connect()
            res.updateDevName()
        return res


    def on_pause(self):                         # can get called multiple times, sometimes no memory objects are set
        IOT.disconnect(True)
        return True

    def on_resume(self):
        connect()

    def on_stop(self):
        IOT.disconnect(False)

Application = GpsTrackerApp()

if __name__ == '__main__':
    Application.run()