#!/bin/env python
#
# Protocol tester TRANH201 Smart Thermostat project

__author__ = 'Stijn Vansummeren'
__date__ = '6 september 2015'

import argparse
import time
from ThermometerServer import ThermometerServer
from ThinThermostatServer import ThinThermostatServer


parser = argparse.ArgumentParser()

parser.add_argument("--central-ip",
                    help="The IP address of the central thermostat. Used to register the thin thermostats"
                         " of the protocol tester with the central thermostat. By default, this is 192.168.10.1. ",
                    default="192.168.10.1")

parser.add_argument("--central-port",
                    help="The port of the central thermostat. Used to register the thin thermostats "
                         "of the VVE with the central thermostat. By default, this is 8080.",
                    default="8080")

parser.add_argument("--no-registration",
                    help="Do not register the thin thermostats with the central thermostat. "
                         "Turned off by default.",
                    default=False,
                    action="store_true")

parser.add_argument("-v", "--verbose",
                    help="Print received HTTP requests to stdout.",
                    action="store_true")

args = parser.parse_args()

#Set up outdoor thermometer server
thermometer_server = ThermometerServer( port=9001 )
servers = [ thermometer_server ]

# Thin thermostats start from port 9001 onwards
port = 9002

for i in range(0,4):
    servers.append( ThinThermostatServer( port=port) )
    port = port + 1

try:
    print("Starting a server for the thermometer and for each thin thermostat-----")
    for server in servers:
        server.start()
    print("\n----All servers started\n\n")

    if not args.no_registration:
        print("Registering thermometer and each thin thermostat with the central thermostat at " + args.central_ip + ":" + str(args.central_port))
        for server in servers:
            server.register(args.central_ip, args.central_port)

    print("\n\n Everything is running. Press Ctrl+C to terminate.\n")
    # Keep going forever
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("""Stopping ...""")
    #for server in servers:
    #    server.terminate()








