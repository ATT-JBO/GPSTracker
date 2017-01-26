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
#from plyer import gps
from plyer import accelerometer
from plyer import battery
from kivy.lib import osc
import datetime

import gpssensor as sensors

IPCPort = 3000
IPCServicePort = 3001
gpsId = 10
batteryId = 11
gpsCoordId = 12
stateId = 13
gpsMinTime = 60000  #milli seconds
gpsMinDistance = 80


#callback: handles values sent from the cloudapp to the device
def on_message(id, value):
    logging.info("unknown actuator: " + id)
iot.on_message = on_message

gpsRunning = False
isStopped = False
gpsService = None
prevGPSData = None
prevBattery = None
prevAccel = None
lastGPSMeasuredAt = None

def on_location(**kwargs):
    try:
        global prevGPSData, lastGPSMeasuredAt
        if prevGPSData and round(kwargs['lat'], 4) == prevGPSData['lat'] and round(kwargs['long'], 4) == prevGPSData['long']: #same location, so stop the gps
            pauseGPSService()
        else:
            lastGPSMeasuredAt = datetime.datetime.now()
        prevGPSData = {'lat': round(kwargs['lat'], 4), 'long': round(kwargs['lon'], 4)}
        if iot.DeviceId:                                            # could be that we are not yet connected.
            iot.sendValueHTTP(prevGPSData, gpsCoordId)                  # for easy tracking on a map.
    except Exception as e:
        sendMsg('on_location failed: ' + e.message)
        logging.exception("on_location failed")

#def isBetterLocation(prev, current):
#    if not prev:
#        return True
#    timeDelta = current['time'] - prev['time']
#    isReall

def sendMsg(message):
    """sends a message to the platform and to the UI part of the app."""
    osc.sendMsg('/update', [message, ], port=IPCPort)
    iot.sendValueHTTP(message, stateId)

def device_callback(message, *args):
    global gpsMinTime
    try:
        iot.DeviceId = message
        if iot.DeviceId:
            iot.connect("tasty.allthingstalk.io")
            iot.addAsset(stateId, "state", "current state of the device", False, "string")
            iot.addAsset(gpsCoordId, "location - coordinates", "location, using new lib, expresed in coordinates", False, '{"type": "object","properties": {"lat": { "type": "number" },"long": { "type": "number" }}}')
            iot.addAsset(batteryId, "battery level", "current battery level", False, "number")
            try:
                minTime = iot.getAssetState("interval")
                if not minTime:
                    minTime = 60
                else:
                    minTime = minTime['value']
            except:
                logging.exception("failed to get interval, switching to default")
                minTime = 60
            gpsMinTime = minTime * 1000
            iot.close()                 # keep connection closed for battery consumption optimisation.
    except Exception as e:
        sendMsg('failed to connect to ATT: ' + e.message)
        logging.exception("failed to connect to ATT")

def stop_callback(message, *args):
    global gpsService, isStopped
    logging.info("stopping gps")
    pauseGPSService(False)
    gpsService = None
    sendMsg('stopped gps')
    isStopped = True
    logging.info("stopped gps")


def pauseGPSService(activateAcceleroMeter = True):
    """stops the gps service but without destroying it, so it will pick up again once the user starts moving."""
    global isStopped, gpsService, gpsRunning
    if gpsService:
        try:
            logging.info("pausing gps")
            gpsService.stop()
            if activateAcceleroMeter:
                accelerometer.enable()
            gpsRunning = False
            logging.info("paused gps")
            sendMsg('paused gps')
        except Exception as e:
            sendMsg('failed to pause GPS: ' + e.message)
            logging.exception("failed to pause gps")

def createGPSService():
    global gpsService
    splitVal = os.getenv('PYTHON_SERVICE_ARGUMENT').split('|')
    try:
        if len(splitVal) > 3:
            iot.ClientId = splitVal[2]
            iot.ClientKey = splitVal[3]
            device_callback(splitVal[1])
        gpsService = sensors.GPSCoarseSensor()
    except Exception as e:
        sendMsg('failed to create GPS: ' + e.message)
        logging.exception("failed to create gps")

def startGPS():
    """start up the GPS"""
    global batteryAtStart, gpsRunning, lastGPSMeasuredAt, prevAccel
    if gpsService:
        try:
            gpsService.configure(on_location=on_location)
            gpsService.start(gpsMinTime, gpsMinDistance)
            accelerometer.disable()
            prevAccel = None
            logging.info("gps started")
            sendMsg('gps started')
            lastGPSMeasuredAt = datetime.datetime.now()
            gpsRunning = True
        except Exception as e:
            sendMsg('failed to start GPS: ' + e.message)
            logging.exception("failed to start gps")

def startOsc():
    """start up the communication between service and main app"""
    osc.init()
    oscid = osc.listen(ipAddr='127.0.0.1', port=IPCServicePort)
    osc.bind(oscid, device_callback, '/device')
    osc.bind(oscid, stop_callback, '/stop')
    return oscid


def processBattery():
    global prevBattery
    try:
        curVal = battery.status['percentage']
        if not prevBattery or curVal != prevBattery:
            iot.sendValueHTTP(curVal, batteryId)
        prevBattery = curVal
    except Exception as e:
        sendMsg('failed to update battery: ' + e.message)
        logging.exception("failed to update battery")


def checkAcceleroMeter():
    global prevAccel
    if accelerometer.acceleration and not None in accelerometer.acceleration:
        curCal = sum(accelerometer.acceleration)
        if not prevAccel:
            prevAccel = curCal
        elif prevAccel + 5 <= curCal or prevAccel - 5 >= curCal:
            startGPS()
        else:
            prevAccel = curCal



if __name__ == '__main__':
    oscid = None
    try:
        oscid = startOsc()
        createGPSService()
        startGPS()
    except NotImplementedError:
        import traceback
        traceback.print_exc()
        logging.error('GPS is not implemented for your platform')
    while not isStopped:
        try:
            if oscid:
                osc.readQueue(oscid)
            processBattery()
            curTime = datetime.datetime.now()
            if gpsRunning == False and isStopped == False:
                checkAcceleroMeter()
            elif lastGPSMeasuredAt and lastGPSMeasuredAt + datetime.timedelta(seconds=140) <= curTime:        #if we didn't receive a GPS fix in 140 seconds, then we are still at the same location, start the accelerometer and stop the GPS to save battery
                pauseGPSService(True)
            sleep(.2)
        except Exception as e:
            logging.exception('main loop failure')
            sendMsg('main loop failure: ' + e.message)