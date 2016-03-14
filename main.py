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


appConfigFileName = 'app.config'
IPCPort = 3000
IPCServicePort = 3001

class Credentials():
    def __init__(self):
        self.userName = ''
        self.password = ''
        self.server = ''
        self.broker = ''

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



def IPCCallback(message, *args):
    logging.info('got message: %s' % message)

class MainWindow(Widget):
    destination = StringProperty('Unknown')
    selectedDeviceName = StringProperty('Select device')
    isRunning = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.service = None
        super(MainWindow, self).__init__(**kwargs)

    def getSettings(self):
        self.config = ConfigParser()
        self.credentials = Credentials()
        if self.config.read(appConfigFileName):
            if self.config.has_option('general', 'device'):
                self.device = self.config.get('general', 'device')
            else:
                self.device = None
            if self.config.has_option('general', 'asset'):
                self.asset = self.config.get('general', 'asset')
            else:
                self.asset = None
            if self.config.has_option('general', 'isRunning'):
                self.isRunning = self.config.get('general', 'isRunning')

            if self.config.has_option('general', 'userName'):
                self.credentials.userName = self.config.get('general', 'userName')
            if self.config.has_option('general', 'password'):
                self.credentials.password = self.config.get('general', 'password')
            if self.config.has_option('general', 'server'):
                self.credentials.server = self.config.get('general', 'server')
            if self.config.has_option('general', 'broker'):
                self.credentials.broker = self.config.get('general', 'broker')

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

    def on_isRunning(self, instance, value):
        """save the isRunning state, so we know the correct value, next time the app is opened"""
        if not self.config.has_section('general'):
            self.config.add_section('general')
        self.config.set('general', 'isRunning', value)
        with open(appConfigFileName, 'w') as f:
            self.config.write(f)

    def saveConfig(self):
        if not self.config.has_section('general'):
            self.config.add_section('general')
        self.config.set('general', 'device', self.device)
        self.config.set('general', 'asset', self.asset)
        self.config.set('general', 'userName', self.credentials.userName)
        self.config.set('general', 'password', self.credentials.password)
        self.config.set('general', 'server', self.credentials.server)
        self.config.set('general', 'broker', self.credentials.broker)
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
        dlg = CredentialsDialog(self.credentials, self.credentialsChanged)
        dlg.open()

    def credentialsChanged(self, newCredentials):
        IOT.disconnect(False)
        self.credentials = newCredentials
        self.connect()
        self.updateDevName()
        self.saveConfig()

    def connect(self):
        try:
            IOT.connect(self.credentials.userName, self.credentials.password,self.credentials.server, self.credentials.broker)
            logging.info("connected")
        except Exception as e:
            showError(e)

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
            service = AndroidService('my gps service', 'running')
            if self.device:
                service.start(level + '|' + self.device + '|' + self.credentials.userName + '|' + IOT._brokerPwd)
            else:
                service.start(level)
            self.service = service

    def stopService(self):
        if self.isRunning:
            if self.service:
                osc.sendMsg('/stop', [''], port=IPCServicePort)
                self.service.stop()
        self.isRunning = False


class GpsTrackerApp(App):
    def build(self):
        self.credentials = None
        osc.init()
        res = MainWindow()
        res.getSettings()
        if res.credentials.userName and res.credentials.password:
            res.connect()
            res.updateDevName()
        return res


    def on_pause(self):                         # can get called multiple times, sometimes no memory objects are set
        IOT.disconnect(True)
        return True

    def on_resume(self):
        self.connect()

    def on_stop(self):
        IOT.disconnect(False)

Application = GpsTrackerApp()

if __name__ == '__main__':
    Application.run()