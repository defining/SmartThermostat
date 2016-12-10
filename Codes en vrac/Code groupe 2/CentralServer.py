# -*- coding: utf-8 -*-

from bottle import request, template, abort, static_file, Bottle
from threading import Thread
from TheDatabase import Database
from operator import itemgetter


class CentralServer(object):
    def __init__(self, host="localhost", port=8080):
        self._host = host
        self._port = port
        self._app = Bottle()
        self._route()
        self._server = None
        self._started = False
        self._type = "central"
        self.registered_devices = []
        self.flag = True
        self.temperature = 25

    def _route(self):
        self._app.route('/register', method="PUT", callback=self.registerDevice)
        self._app.route('/dashboard', method="GET", callback=self.dashboard)
        self._app.route('/static/<filename:path>', method="GET", callback=self.server_static)
        self._app.route('/temperature', method="POST", callback=self.setpoint_temperature)
        self._app.route('/stop', method="POST", callback=self.stop)

    def start(self):
        """Starts the server in a background process, only if not already started"""
        if not self._started:
            self._started = True
            self._server = Thread(target=self._app.run,
                                  kwargs=dict(host=self._host, port=self._port, debug=True, reloader=False))
            self._server.daemon = True
            self._server.start()
            return self._server

    def join(self):
        """Joins the server process with the calling thread. Calling thread blocks until server process is complete."""
        if self._started:
            self._server.join()

    def terminate(self):
        """Terminates the server process"""
        if self._started:
            self._started = False
            self._server.terminate()

    def registerDevice(self):
        """This method will be called for every PUT request on the /register sever
        We only accept JSON"""

        if request.content_type != 'application/json':
            abort(400, 'Expected content_type application/json')
        device_to_register = request.json
        print(device_to_register)
        self.registered_devices.append(device_to_register)
        print("I received a PUT request to /register with the following data: %s" % device_to_register)

    def dashboard(self):
        """Return a HTML dashboard illustrating the state"""
        n = len(self.registered_devices)
        database = Database('template.db')
        database.cur.execute('''SELECT ip, nom, statut, temperature, presence, valve FROM sensor''')
        data = database.cur.fetchall()[-n:]
        data.sort(key=itemgetter(1))
        database.cur.close()
        output = template("table.tpl", rows=data)
        return output

    def server_static(self, filename):
        """Handle the CSS code"""
        return static_file(filename=filename, root='static/')

    def setpoint_temperature(self):
        """Change the setpoint temperature while you press the specific HTML button
        See in the dashboard"""
        self.flag = True
        self.temperature = float(request.forms.get('temperature'))

    def stop(self):
        """Stop the heating process while you press the specific HTML button
        See in the dashboard"""
        self.flag = False