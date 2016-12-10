__author__ = 'stijn'

from bottle import route,  get, put, post, delete, request, response, template, abort, run, static_file
from threading import Thread
import sys
import time

#----------------------------------------------------------------------
#- REST methods
#----------------------------------------------------------------------
@put('/register')
def registerDevice():
    "This method will be called for every PUT request on the /register server"

    #We only accept json
    if request.content_type != 'application/json':
        abort(400, 'Expected content_type application/json')

    device_to_register = request.json
    print("I received a PUT request to /register with the following data: %s" % device_to_register)

#----------------------------------------------------------------------
#- REST methods
#----------------------------------------------------------------------
@get('/dashboard')
def dashboard():
    "Return a HTML dashboard illustrating the state"
    return "Your dashboard should be here!"

#----------------------------------------------------------------------
#- Main
#----------------------------------------------------------------------

def start_web_server(iface="localhost", port=8080):
    """Starts the bottle web server"""

    server = Thread(target=run,
                    kwargs=dict(host=iface, port=port, debug=True, reloader = False))
    server.daemon = True  #server should exit when main thread exits
    server.start()
    return server


def main():
    try:
        iface = "192.168.10.1" # if you are not running on the pi, change this to the ip address of your computer, or to "localhost"
        port = 8080
        start_web_server(iface,port)
        print("Web server is running at %s:%s. Point your webbrowser to http://%s:%s/dashboard for a dashboard " % (iface,port,iface,port))
        while True:
            # TODO: This is where you would poll registered devices,
            # and do control logic
            time.sleep(5)

    except KeyboardInterrupt:
        sys.stdout.write("Aborted by user.\n")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
