# -*- coding: utf-8 -*-
"""Base class for simulated devices.

Devices can be e.g., thin thermostat and thermometer.
"""

__author__ = "Stijn Vansummeren"
__date__ = "2 September 2015"

from bottle import Bottle, template
from multiprocessing import Process
from threading import Thread
import requests #for http requests
import json
import sys


class Server:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._app = Bottle()  # create bottle app
        self._route()  # set up routes
        self._server = None
        self._started = False
        self._type = "NONE" #children need to override

    def _route(self):
        # set up routes. We cannot use the bottle decorators since those only work on functions, not object methods
        # see http://stackoverflow.com/questions/8725605/bottle-framework-and-oop-using-method-instead-of-function
        pass

    def _start(self, quiet=True):
        print("starting... " + self.__class__.__name__ + " at http://" + self._host + ":" + str(self._port))
        self._app.run(host=self._host, port=self._port, quiet=quiet)

    def start(self):
        """Starts the server in a background process, only if not already started"""
        if not self._started:
            self._started=True
            self._server = Thread(target=self._start, kwargs=dict())
            # Alternative implementation: use Process, but then a separate process is spawned with its own copy of the memory (no shared mem)
            # self._server = Process(target=self._start, kwargs=dict())
            self._server.daemon = True
            self._server.start()  # server starts in the background


    def join(self):
        """Joins the server process with the calling thread. Calling thread blocks until server process is complete."""
        if self._started:
            self._server.join()

    def terminate(self):
        """Terminates the server process"""
        if self._started:
            self._started = False
            self._server.terminate()

    def register(self,host,port):
        """Register device by making a PUT request to central thermostat"""

        dev={ "ip": self._host, "port": self._port,"type": self._type, }
        headers = {'content-type': 'application/json'}
        url = "http://%s:%s/register" % (host,port)
        print("PUT with content-body %s to %s" % (dev,url))

        try:
            r = requests.put(url, data=json.dumps(dev), headers=headers)
            if r.status_code == requests.codes.ok:
                print("... registration ok")
            else:
                print("... unexpected return code: " + r.status_code)
        except requests.exceptions.ConnectionError as e:
            print("Registration failed:")
            print(e)
            sys.exit(-1)
        except requests.exceptions.HTTPError as e:
            print("HTTP error while registering %s:" % str(dev))
            print(e)




