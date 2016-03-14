__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging

from plyer.platforms.android import activity
from jnius import autoclass, java_method, PythonJavaClass

Looper = autoclass('android.os.Looper')
Context = autoclass('android.content.Context')
LocationManager = autoclass('android.location.LocationManager')

class _LocationListener(PythonJavaClass):
    __javainterfaces__ = ['android/location/LocationListener']

    def __init__(self, root):
        self.root = root
        super(_LocationListener, self).__init__()

    @java_method('(Landroid/location/Location;)V')
    def onLocationChanged(self, location):
        self.root.on_location(
            lat=location.getLatitude(),
            lon=location.getLongitude(),
            speed=location.getSpeed(),
            bearing=location.getBearing(),
            altitude=location.getAltitude(),
            accuracy=location.getAccuracy())

    @java_method('(Ljava/lang/String;)V')
    def onProviderEnabled(self, status):
        if self.root.on_status:
            self.root.on_status('provider-enabled', status)

    @java_method('(Ljava/lang/String;)V')
    def onProviderDisabled(self, status):
        if self.root.on_status:
            self.root.on_status('provider-disabled', status)

    @java_method('(Ljava/lang/String;ILandroid/os/Bundle;)V')
    def onStatusChanged(self, provider, status, extras):
        if self.root.on_status:
            s_status = 'unknown'
            if status == 0x00:
                s_status = 'out-of-service'
            elif status == 0x01:
                s_status = 'temporarily-unavailable'
            elif status == 0x02:
                s_status = 'available'
            self.root.on_status('provider-status', '{}: {}'.format(
                provider, s_status))


class GPSBase():
    def stop(self):
        self._location_manager.removeUpdates(self._location_listener)
        logging.info("gps stopped")

    def configure(self, on_location, on_status=None):
        '''Configure the GPS object. This method should be called before
        :meth:`start`.

        :param on_location: Function to call when receiving a new location
        :param on_status: Function to call when a status message is received
        :type on_location: callable, multiples keys/value will be passed.
        :type on_status: callable, args are "message-type", "status"

        .. warning::

            The `on_location` and `on_status` callables might be called from
            another thread than the thread used for creating the GPS object.
        '''
        self.on_location = on_location
        self.on_status = on_status
        if not hasattr(self, '_location_manager'):
            self._location_manager = activity.getSystemService(Context.LOCATION_SERVICE)
            self._location_listener = _LocationListener(self)
        logging.info("gps configured")

class GPSCoarseSensor(GPSBase):
    def start(self, minTime = 1000, minDistance = 1):
        logging.info("starting coarse")
        providers = self._location_manager.getProviders(False).toArray()
        for provider in providers:
            prov = self._location_manager.getProvider(provider)
            if prov.getAccuracy() == 1:    # fine
                self._location_manager.requestLocationUpdates(
                    provider,
                    minTime,  # minTime, in milliseconds
                    minDistance,  # minDistance, in meters
                    self._location_listener,
                    Looper.getMainLooper())
                logging.info("started coarse")
                break

class GPSFineSensor(GPSBase):
    def start(self, minTime = 1000, minDistance = 1):
        providers = self._location_manager.getProviders(False).toArray()
        for provider in providers:
            prov = self._location_manager.getProvider(provider)
            if prov.getAccuracy() == 1:    # fine
                self._location_manager.requestLocationUpdates(
                    provider,
                    minTime,  # minTime, in milliseconds
                    minDistance,  # minDistance, in meters
                    self._location_listener,
                    Looper.getMainLooper())
                logging.info("started fine")
                break
        #logging.info("starting fine")
        #self._location_manager.requestLocationUpdates(
         #   'gps',
         #   minTime,  # minTime, in milliseconds
         #   minDistance,  # minDistance, in meters
         #   self._location_listener,
         #   Looper.getMainLooper())


