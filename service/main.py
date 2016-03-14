__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
logging.getLogger().setLevel(logging.INFO)

import attiot as iot

from time import sleep
import os
from plyer import gps
from kivy.lib import osc
import datetime

import gpssensor as sensors

IPCPort = 3000
IPCServicePort = 3001
gpsId = 10

#callback: handles values sent from the cloudapp to the device
def on_message(id, value):
    logging.info("unknown actuator: " + id)
iot.on_message = on_message

isStopped = False

def on_location(**kwargs):
    try:
        if iot.DeviceId:                                            # could be that we are not yet connected.
            iot.send("{lat},{lon}".format(**kwargs), gpsId)
    except Exception as e:
        logging.exception("on_location failed")

def device_callback(message, *args):
    logging.info("got a message! %s" % message)
    iot.DeviceId = message
    if iot.DeviceId:
        iot.connect()
        iot.addAsset(gpsId, "location - new", "location, using new lib", False, "string")
        iot.subscribe()

def stop_callback(message, *args):
    global isStopped, gpsService
    if gpsService:
        logging.info("stopping gps")
        gpsService.stop()
        gpsService = None
        isStopped = True

gpsService = None

if __name__ == '__main__':
    try:
        osc.init()
        oscid = osc.listen(ipAddr='127.0.0.1', port=IPCServicePort)
        osc.bind(oscid, device_callback, '/device')
        osc.bind(oscid, stop_callback, '/stop')
        splitVal = os.getenv('PYTHON_SERVICE_ARGUMENT').split('|')
        if len(splitVal) > 3:
            iot.ClientId = splitVal[2]
            iot.ClientKey = splitVal[3]
            device_callback(splitVal[1])
        if splitVal[0] == 'fine':
            gpsService = sensors.GPSFineSensor()
        elif splitVal[0] == 'coarse':
            gpsService = sensors.GPSCoarseSensor()
        else:
            gpsService = None
        if gpsService:
            gpsService.configure(on_location=on_location)
            gpsService.start(15000, 15)
            logging.info("gps started")
        else:
            logging.error("unknown gps logging level requested: " + level)
    except NotImplementedError:
        import traceback
        traceback.print_exc()
        logging.error('GPS is not implemented for your platform')
    while not isStopped:
        try:
            osc.readQueue(oscid)
            sleep(.1)
        except:
            logging.exception('main loop failure')