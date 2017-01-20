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
            value = {"lat": kwargs['lat'], "lon": kwargs['lon']}
            iot.sendValueHTTP(value, gpsId)
    except Exception as e:
        logging.exception("on_location failed")

def device_callback(message, *args):
    logging.info("got a message! %s" % message)
    iot.DeviceId = message
    if iot.DeviceId:
        iot.connect("tasty.allthingstalk.io")
        if gpsService:
            if isStopped == False:
                gpsService.stop()
            interval = iot.getAssetState("interval")
            gpsService.start(int(interval) * 1000, 30)
            logging.info("gps started")

def stop_callback(message, *args):
    global isStopped, gpsService
    if gpsService:
        logging.info("stopping gps")
        gpsService.stop()
        gpsService = None
        isStopped = True
        logging.info("stopped gps")



gpsService = None

if __name__ == '__main__':
    try:
        osc.init()
        oscid = osc.listen(ipAddr='127.0.0.1', port=IPCServicePort)
        osc.bind(oscid, device_callback, '/device')
        osc.bind(oscid, stop_callback, '/stop')
        splitVal = os.getenv('PYTHON_SERVICE_ARGUMENT').split('|')
        gpsService = sensors.GPSCoarseSensor()
        if gpsService:
            gpsService.configure(on_location=on_location)
        if len(splitVal) > 3:
            iot.ClientId = splitVal[2]
            iot.ClientKey = splitVal[3]
            device_callback(splitVal[1])
        else:
            logging.error("no credentials, can't start gps")
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