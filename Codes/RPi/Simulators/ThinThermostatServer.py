# -*- coding: utf-8 -*-
"""Serves a (simulated) thin thermostat over HTTP according specified smart thermostat communication protocol.
"""

__author__ = "Stijn Vansummeren"
__date__   = "2 September 2015"

import random
from .Server import Server #MODIFIED

from bottle import route,  get, put, post, delete, request, response, template, abort, run, HTTPResponse

class ThinThermostatServer(Server):
    """Serves a (simulated) ThinThermostat device over HTTP according to the specified smart thermostat communication protocol."""

    def __init__(self, init_temp=10, host="localhost", port="9001"): #MODIFIED: init_temp arg added
        Server.__init__(self, host, port)
        self._type="thin"
        self._actuation_value = 0
        self.temperature = init_temp # MODIFIED : attribute added
        self.presence = 'false' # MODIFIED: attribute added

    def _route(self):
        #set up routes. We cannot use the bottle decorators since those only work on functions, not object methods
        #see http://stackoverflow.com/questions/8725605/bottle-framework-and-oop-using-method-instead-of-function

        self._app.route('/temperature', method="GET", callback=self._temperature)
        self._app.route('/presence', method="GET", callback=self._presence)
        self._app.route('/valve', method="GET", callback=self._actuation_value)
        self._app.route('/valve', method="PUT", callback=self._actuate_valve)

    def _temperature(self):
        """Queries temperature"""
        response.content_type="text/plain"
        return str(self.temperature) # MODIFIED (no more random)


    def _presence(self):
        """Queries presence"""
        response.content_type="text/plain"
        #if random.randint(0,1) == 0:
        #    return "false"
        #else:
        #    return "true"
        return self.presence

    def _actuate_valve(self):
        """Sets the new actuation value"""
        if request.content_type != "text/plain":
            abort(400, "Expected content_type: " + "text/plain")
            
        value = 0
        try:
            value = int(request.body.read())
        except ValueError:
            abort(400, "Request body should contain integer literal between 0 and 100.")

        if ((value < 0) or (value > 100)):
            abort(400, "Request body should contain integer literal between 0 and 100.")

        self._actuation_value = value
        return HTTPResponse(status=200) #MODIFIED: bottle. removed

    def _actuation_value(self):
        """Gets the current actuation value"""
        response.content_type="text/plain"
        return str(self._actuation_value) #MODIFIED: () removed!





