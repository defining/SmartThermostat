__version__ = '0.2'

from ThermoThings import ThermoServer as ts 
from ThermoThings import Data

import Utils

import cmd
import logging
import sys
import argparse # for command line args


class ThermoServerShell(cmd.Cmd):
    """
        The simplest method to run, test and control the server.
        Inhertted from Cmd to have all the cool functionnalities of a command line interface.
    """

    intro = (
            "------------------------------------------------------------------\n"
            "-------------------------- ThermoServer --------------------------\n"
            "------------------------------------------------------------------\n"
            
            )

    prompt = '>>>'

    ruler = ''
    doc_header = 'Available commands : '

    def __init__(self, server):
        super().__init__('tab', None, None)
        self.s = server


    def preloop(self):
        print(self.intro)
        self.intro = ''
        self.do_help('')



    def postloop(self):
        print('Server stopping...')
        self.s.stop()
        print('Server stoped.')


    def do_devices(self, arg):
        """Shows the measures of every connected device"""
        if len(arg.split()) != 0:
            print('devices takes no arg')
        else:
            print('Retrieving measures for each connected device. This can take several seconds...')
            print(self.s.get_devices_measures())


    def do_status(self, arg):
        """Tells if the server is running, if it's saving data and tells the number of connected devices"""
        if len(arg.split()) != 0:
            print('status takes no arg')
        else:
            print(self.s.status())

    def do_sumary(self, arg):
        """Prints a small report on the server state."""
        self.s.print_summary()

        
    def do_setvalve(self, arg):
        """Usage : setvalve [device name] [0-100]
        Send a request to change the valve on the specified remote-device"""
        args = arg.split()
        if len(args) != 2:
            print('2 arguments were expected; ' + str(len(args)) + 'given.')
        else:
            device_name = args[0]
            new_value = args[1]
            if new_value.isdigit() and 0 <= int(new_value) <= 100:
                device = self.s.get_device_by_name(device_name)
                if device:
                    device.get_sensors_by_name('valve').set_option(int(new_value))
                else:
                    print('No device named ' + device_name + ' was found.')
            else:
                print('Second argument must be a digit between 0 and 100')

    def complete_setvalve(self, arg):
        # TODO
        pass

    def do_getdata(self, arg):
        """Usage : getdata [nbr]
        (nbr = 10 by default)
        Prints the last [nbr] entries stored in the database."""
        args = arg.split()
        if len(args) > 1:
            print('1 or 0 argument were expected; ' + str(len(args)) + 'given.')
        else:
            if args and isdigit(args[0]):
                nbr = int(args[0])
            else:
                print('No nbr specified. 10 by default')
                nbr = 10

            if len(self.s.database.tables.keys()) == 0:
                print('No tables in database (is there a connected device?)')
            else:
                for device_table in self.s.database.tables.values():
                    print('Last ' + str(nbr) + ' stored entries for ' + device_table.table_name + ' : ')
                    res = device_table.get_last_n_measures(nbr)
                    print(res)
                    print('\n\n')

    def do_exit(self, line):
        """Stop the server, you can use ^D"""
        return True
    do_EOF = do_exit


parser = argparse.ArgumentParser()
parser.add_argument('--log', action='store', default='WARNING', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
parser.add_argument('--no-req-handling', action='store_false', default=True)
parser.add_argument('--no-data-getting', action='store_false', default=True)

args = dict(parser.parse_args()._get_kwargs())

logging.getLogger("requests").setLevel(logging.WARNING) # TODO: Is this really at the appropriate place?..

numeric_level = getattr(logging, args['log'], None)
logging.basicConfig(level=numeric_level) # --log=DEBUG



print('Server starting...')
#s = ts.ThermoServer(8080, 25, 'data.sqlite3') #port, period, database_name
s = ts.ThermoServer('thermoConfig.cfg')
s.run(args['no_req_handling'], args['no_data_getting'])
print('Server started on port %s.' % str(s.cfg['port']))

shell = ThermoServerShell(s)
shell.cmdloop()

print("Program ended.")
