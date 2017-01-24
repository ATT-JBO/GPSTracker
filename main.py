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
from kivy.clock import Clock
if platform == 'android':
    from android import AndroidService


from ConfigParser import *

import attiotuserclient as IOT
from errors import *
import data


appConfigFileName = 'app.config'
IPCPort = 3000
IPCServicePort = 3001

IOT._app_id = "web"     # for debugging on tasty.

def isServiceRunning():
    '''check if service is running '''
    from plyer.platforms.android import activity
    from jnius import autoclass
    import sys
    Context = autoclass('android.content.Context')
    manager = activity.getSystemService(Context.ACTIVITY_SERVICE)
    for myService in manager.getRunningServices(sys.maxint).toArray():
        if str(myService.service.flattenToString()) == "gpstracker.org.test.gpstracker/org.renpy.android.PythonService":
            return True
    return False

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
    currentstatus = StringProperty('not yet started')
    selectedDeviceName = StringProperty('Select device')
    isRunning = BooleanProperty(False)

    def __init__(self, **kwargs):
        if platform == 'android':
            self.isRunning = isServiceRunning()
            if self.isRunning:
                self.service = AndroidService('my gps service', 'running')
                self.currentstatus = "service was running"
            else:
                self.service = None
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
        with open(appConfigFileName, 'w') as f:
            self.config.write(f)

    def showSelectDevice(self, relativeTo):

        dropdown = DropDown() # auto_width=False, width='140dp'
        devices = IOT.getDevices(data.credentials.groundid)
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
            locationAsset = [asset for asset in assets if str(asset['name']).startswith('prediction_distance_json') ]
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
            if not self.service:
                self.service = AndroidService('my gps service', 'running')
            if self.device:
                self.service.start(level + '|' + self.device + '|' + data.credentials.deviceAuth + '|' + IOT._brokerPwd)
            else:
                self.service.start(level)

    def stopService(self):
        if self.isRunning:
            if self.service:
                osc.sendMsg('/stop', [''], port=IPCServicePort)
                try:
                    self.service.stop()
                    self.currentstatus = "GPS stopped"
                except Exception as e:
                    logging.exception('failed to stop service')
                    self.currentstatus = "failed to stop service: " + e.message

        self.isRunning = False

    def on_update_from_service(self, message, *args):
        self.currentstatus = message[2]

class GpsTrackerApp(App):
    def build(self):
        self.main = MainWindow()
        self.main.getSettings()
        if data.credentials.userName and data.credentials.password:
            connect()
            self.main.updateDevName()
        self.setupOsc()
        return self.main



    def setupOsc(self):
        osc.init()
        oscid = osc.listen(ipAddr='127.0.0.1', port=IPCPort)
        osc.bind(oscid, self.main.on_update_from_service, '/update')
        Clock.schedule_interval(lambda *x: osc.readQueue(oscid), 0)


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