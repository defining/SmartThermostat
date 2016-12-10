# -*- coding: utf-8 -*-
"""Serves a (simulated) outdoor thermometer over HTTP according specified smart thermostat communication protocol.
"""

__author__ = "Stijn Vansummeren"
__date__   = "2 September 2015"

import random
from .Server import Server # MODIFIED

from bottle import route,  get, put, post, delete, request, response, template, abort, run, HTTPResponse

class ThermometerServer(Server):
    """Serves a (simulated) outdoor thermometer over HTTP

    HTTP api conforms to the specified smart thermostat communication protocol."""

    def __init__(self, init_temp=10, host="localhost", port="9000"):
        Server.__init__(self, host, port)
        self._type = "outside"
        self.temperature = init_temp

    def _route(self):
        # set up routes. We cannot use the bottle decorators since those only work on functions, not object methods
        # see http://stackoverflow.com/questions/8725605/bottle-framework-and-oop-using-method-instead-of-function
        self._app.route('/temperature', method="GET", callback=self._temperature)

    def _temperature(self):
        """Queries temperature"""
        response.content_type="text/plain"
        return str(random.uniform(-10,30))

        




