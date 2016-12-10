#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
...
"""
__version__ = '1.3'
__author__ = 'Sercu Stéphane'


from http.server import HTTPServer
import json                             
import threading
import requests
import time
import logging

from Utils import Utils as u                       # Includes RepeatingTimer and RequestRouter
from .Data import ThermoDB
import xml.etree.ElementTree as ET      # For cfg file parsing purpose

from .Pid import PID
from .ThermoModels import ProbabilityModelHandler


class ThermoConfig(dict):
    """
        Parse a specified valid xml configuration file (for the thermostat) and serve the configuration option availlable in it.
        Supported options are:
            - port
            - db_name
            - period
            - device_types
    """

    BASIC_DEVICE_TYPES = {
                            'thin':[{'measure_name':'temperature', 
                                        'measure_type':'REAL', 
                                        'constructor':lambda *args: Sensor('temperature', 'REAL', *args)},
                                    {'measure_name':'presence', 
                                        'measure_type':'INTEGER', 
                                        'constructor':lambda *args: Sensor('presence', 'INTEGER', *args)},
                                    {'measure_name':'valve', 
                                        'measure_type':'INTEGER', 
                                        'constructor':lambda *args: InteractiveSensor('valve', 'INTEGER', *args)}
                                    ],
                            'outside':[{'measure_name':'temperature', 
                                        'measure_type':'REAL', 
                                        'constructor':lambda *args: Sensor('temperature', 'REAL', *args)}
                                    ]
                        }

    DEFAULT_VALUES = {
        'port':8080,
        'period':25,
        'db_name':'data.sqlite3',
        'device_types':BASIC_DEVICE_TYPES
    }


    def __init__(self, cfg_file_path):
        """
            cfg_file_path: (str) path of the configuration file
        """
        super(ThermoConfig, self).__init__()
        self.file_path = cfg_file_path
        self.refresh()

    def refresh(self):
        """
            Parse the config file and update the values.
        """
        try: 
            tree = ET.parse(self.file_path)
            root=tree.getroot()
            self['port'] = self._parse_port(root)
            self['db_name'] = self._parse_db_name(root)
            self['period'] = self._parse_period(root)
            self['device_types'] = self._parse_device_types(root)

        except FileNotFoundError:
            logging.warning("The specified configuration file doesn't exist, default configuration will be applied.")
        

    def _parse_port(self, xml_root):
        """
            Finds and returns the port option in the config file.
        """
        rtn = self.DEFAULT_VALUES['port']
        try:
            rtn = int(xml_root.find('port').text)
            logging.debug('Port found in the configutation file : %s\n'%str(port))
        except Exception as ex:
            logging.warning('No valid port was found in the cfg file. Default port (%s) will be used.' % str(port))
        finally:
            return rtn

    def _parse_db_name(self, xml_root):
        rtn = self.DEFAULT_VALUES['db_name']
        try:
            rtn = xml_root.find('database_name').text
            logging.debug('Path of database found in the configutation file : %s\n'%database_name)
        except Exception as ex:
            logging.warning('No valid database name was found in the cfg file. Default name (%s) will be used.' % str(database_name))
        finally:
            return rtn

    def _parse_period(self, xml_root):
        rtn = self.DEFAULT_VALUES['period']
        try:
            rtn = int(xml_root.find('period').text)
            logging.debug('Period found in the configutation file : %s\n'%str(period))
        except Exception as ex:
            logging.warning('No valid period was found in the cfg file. Default period (%s) will be used.' % str(period))
        finally:
            return rtn

    def _parse_device_types(self, xml_root):
        rtn = self.DEFAULT_VALUES['device_types']
        try:
            device_types={}
            xml_device_types = xml_root.findall('./device_types/device')

            for device in xml_device_types:
                device_name = device.find('device_name').text
                device_types[device_name]=[]
                sensors = device.findall('sensor')
                
                for sens in sensors: 
                    measure_name = sens.find('measure_name').text
                    measure_type = sens.find('measure_type').text
                    sensor_type = sens.find('sensor_type').text
                    constr = self.sensor_constructor(sens)
                        
                    if constr: # If the type of sensor (Interactive or Normal) is correctly specified
                            
                        device_type = {'measure_name':measure_name, 'measure_type':measure_type, 'constructor':constr}
                            
                        device_types[device_name].append(device_type)
                    else:
                        logging.warning("Config parser error: A sensor constructor could'nt be built. measure_name: %s, sensor_type: %s" %(measure_name, sensor_type))

            rtn = device_types # In case of exception, the default value of remote_device_types is kept
                
        except Exception as ex:
            logging.warning('The configuration parser failed to load the supported device types. Check the structure of the configuration file. Only the basic device types (thin and outside) will be initialized')
            logging.exception(ex)
        finally:
            return rtn

    def sensor_constructor(self, xml_sensor, *args):
        """
            Returns a sensor constructor based on xml configuration.
        """
        mn = xml_sensor.find('measure_name').text
        mt = xml_sensor.find('measure_type').text
        sensor_type = xml_sensor.find('sensor_type').text
        
        constr = None
        if sensor_type == 'Normal':
            constr = lambda *args: Sensor(mn, mt, *args)
        elif sensor_type == 'Interactive':
            constr = lambda *args: InteractiveSensor(mn, mt, *args)
        elif sensor_type == 'Local':
            constr = lambda *args: LocalSensor(mn, mt, *args)
        else:
            logging.error("Configuration file error: specified sensor type (%s) not valid (Normal, Interactive or Local intended)"%sensor_type)

        return constr

class ThermoServer:

    def __init__(self, cfg_path):
        """
            Initializes a ThermoServer instance based on a configuration file.
            The configuration file MUST define the supported remote device types 
            and can specify the port, the period of data retrieving and the name 
            of the database.

            TODO: an xml schema validation?
        """
        self.cfg = ThermoConfig(cfg_path)
        #(self.port, self.period, self.database_name, self.remote_device_types) = self._parse_cfg(cfg_path)

        # self.port = 8080
        # self.period = 3
        # self.database_name = 'data.sqlite3'
        # self.remote_device_types = self.BASIC_DEVICE_TYPES

        self.devices = []

        self.database = ThermoDB(self.cfg['db_name'], self.cfg['device_types']) # TODO: private?
        self.db_query_handler = self.database.query_handler


        self._req_handler_thread = threading.Thread() # This thread will handle the registration requests
        self._http_server = None # 

        self._data_getter_thread = u.RepeatingTimer(self.cfg['period'], self.magic_function) # This thread tetrieve data from devices, save the and update valves
        
        self._data_analysis_thread = u.RepeatingTimer(24*3600, self.data_analyse)


        self.thin_presence_predictors = {}

    def data_analyse(self):
        """
            Run math models, using collected data to predict occupancy, heating time, 
        """
        # Update Presence model constant
        for thin, presence_predictor in self.thin_presence_predictors.items():
            presence_predictor.update_probability_model()

        # Update Thermal Properties
        for thin, thermal_property_model in self.thin_thermal_properties:
            thermal_property_model.update()


    def print_summary(self):
        """
            Prints a small report on the server state.
        """
        # Is the server running? on which port? Data getting? Period? database used? Suported device types? Connected devices? 
        print(self.status())
        print(self.cfg['port'])
        print(self.cfg['db_name'])
        print(self.cfg['period'])
        print(self.cfg['device_types'])


    def _start_req_handling(self):
        """
            Start the server and beginig to handle requests.
            It will be running until 'shutdown' method is called.
        """
        server_address = ('', self.cfg['port'])

        # Every supported requested, sorted by type, must be associated to a callback here
        routes = {'PUT':{'/register':self.register_new_device}}

        handler_class = lambda *args: u.RequestRouter(routes, *args)
        
        self._http_server = HTTPServer(server_address, handler_class)

        self._http_server.serve_forever() # This blocks the execution line, the eventual following code will be executed after the request handling process stop


    def register_new_device(self, request_data):
        """
            Callback function who registers a new device from request data.
            request_data is a dictionnary with 2 keys : headers and content.
                headers is a list of tuples (key, value)
                content is a bytes list
            Returns an http response code.
        """
        return_code = 200 # OK by default

        try:
            logging.info('Registration request received.')
            json_content = json.loads(request_data['content'].decode('utf-8'))

            if 'port' in json_content.keys() and 'ip' in json_content.keys() and 'type' in json_content.keys(): #TODO : Validation using jsonschema
                
                device_type = json_content['type']
                device_ip = json_content['ip']
                device_port = json_content['port']
                device_name = 'device' + str(len(self.devices))
                print('Registering...')
                d = self._build_device_of_type(device_type, device_ip, device_port, device_name)
                
                if d != None:
                    self.devices.append(d)

                    cols = {sens.measure_name: sens.measure_type for sens in d.sensors}

                    self.database.query_handler.register_device(d.name, d.ip)
                    logging.info('Device \'%s\'created and added in database', d.name)
                else:
                    logging.warning('Device creation failed.')
                    return_code = 500 # Internal Server Error
            else:
                logging.warning('Received file is not correct json. 501 will be sent.')
                return_code = 501 # Not Implenmented

        except ValueError as exc:
            logging.error('An exception have been handled : %s. 501 will be sent.' % exc.value)
            return_code = 501 # Not Implenmented

        finally:
            return return_code

        
    def get_device_by_name(self, name):
        # TODO: maybe store RemoteDevices in a dictionnary {str_name:RemoteDevice}?
        # TODO: what if 2 samely named RemoteDevices?
        """
            Returns the first connected device matching the specified name.
            Return None of no device matched.
        """
        match = None
        for device in self.devices:
            if device.name == name:
                match = device
                break
        return match


    def get_devices_measures(self):
        """
            Returns a dictionnary of dictionnaries containing the measures of each sensors (for each device). 
            Each measure is associated to his name, and each set of measures is associated to the name of the device they belong.
            Ex of return value : {'device0':{'temperature':20, 'presence':True, 'valve':80}, 'device2':{'Temperature':20}}
        """
        devices_measures = {} #TODO : detect the not connected devices and remove them from the list.
        for device in self.devices:
            logging.debug("Fetching measures for %s." % device.name)
            devices_measures[device.name] = device.get_measures()

        return devices_measures

    def save_devices_measures(self):
        """
            Get all the measures of each connected device and store them in the database.
        """
        devices_measures = self.get_devices_measures()
        logging.debug('Saving all measures : ' + str(devices_measures))
        self.database.query_handler.save_measure_of_all_devices(devices_measures)

    # def update_valves(self):
    #     """
    #         Use PID, the desired temperature and the current 
    #         temperature for each device to update the valve state.
    #     """
    #     # TODO: determine desired tempearture 
    #     target_temp = 20.0
    #     for device in self.devices:
    #         if device.type == 'thin': # TODO: maybe a way to generalise 'thin' to 'any device that have an interactiveSensor that have to be PID controlled'
    #             valve = device.get_sensors_by_name('valve')
    #             valve.pid.set_point(target_temp)
    #             valve.pid.update(device.get_sensors_by_name('temperature').value)

    def magic_function(self):
        """
            Collects measures, save them, and update valves.
        """
        devices_measures = {}
        target_temp = 20.0
        fallback_temp = 15.0

        for device in self.devices:
            logging.debug("Fetching measures for %s." % device.name)
            devices_measures[device.name] = device.get_measures()

            if device.type == 'thin':# TODO: maybe a way to generalise 'thin' to 'any device that have an interactiveSensor that have to be PID controlled'
                valve = device.get_sensors_by_name('valve')
                #if valve.pid.set_point != target_temp:
                #    valve.pid.setPoint(target_temp)

                try:
                    

                    if devices_measures[device.name]['presence']: # If presence...
                        valve.pid.update(devices_measures[device.name]) # Reactive
                        #devices_measures[['target_temp'] = target_temp
                    elif u.TimeOperator.get_number_of_days_since_thermostat_launch() >= 8:    #the code will a wait whole week before becoming predicitive
                        t = u.TimeOperator.get_elapsed_seconds_since_midnight()
                        delta_t = valve.pid.get_heating_time()
                        if not device_name in self.thin_presence_predictors:
                            self.thin_presence_predictors[device.name] = ProbabilityModelHandler(self.database.query_handler)
                            # TODO: probability model never  updated...
                        if self.thin_presence_predictors[device.name].get_probability(t + delta_t) >= 0.5:#self.trigger_value
                            valve.pid.update(devices_measures[device.name])

                    else:
                        valve.pid.update(fallback_temp)      

                    #current_valve = int(devices_measures[device.name]['valve']) # TODO: the rturned value can be None, cast will produce unwanted results
                    #pid_regulation = int(valve.pid.update(float(devices_measures[device.name]['temperature']))) # TODO: (float casting) What if the value returned by the remoteDevice isn't a numeric value?
                    valve_percent =  valve.pid.update(devices_measures[device.name])

                    valve.set_option(valve_percent)

                    logging.info("Valve update for device '%s'"%device.name)
                except Exception as e:
                    logging.error("An exception during the valve actuation: \n" + str(e))

        logging.debug('Saving all measures : ' + str(devices_measures))
        self.database.query_handler.save_measure_of_all_devices(devices_measures)

    
    def status(self):
        """
            Returns a dictionnary with those keys : 
                - req_handling : True or False, indicating if the server is handling requests
                - connected_devices : int, number of connected devices
        """
        req_handling = self._req_handler_thread.is_alive() # As long as the thread is running, the requests handling is operative
        data_getting = self._data_getter_thread.is_alive() 
        connected_devices = len(self.devices)

        status = {'req_handling':req_handling, 'data_getting':data_getting, 'connected_devices':connected_devices}
        return status

    def run(self, req_handling=True, data_getting=True):
        """
            Start the requests handling and measure saving in a new threads.
        """
        # Request handling setup
        if req_handling: self.start_req_handling()

        # Periodic data saving setup
        if data_getting: self.start_data_getting()


    def start_req_handling(self):
        if not self.status()['req_handling']:
            self._req_handler_thread = threading.Thread(None, self._start_req_handling, 'RequestHandlingThread')
            self._req_handler_thread.start()
            logging.info("Request handling is started.")
        else:
            logging.warning("Requests handling is already running.")

    def start_data_getting(self):
        if not self.status()['data_getting']:
            self._data_getter_thread = u.RepeatingTimer(self.cfg['period'], self.magic_function)
            self._data_getter_thread.start()
            logging.info("Periodic data fetching & saving started.")
        else:
            logging.warning("Periodic ata fetching and saving is already running.")


    def stop(self):
        """
            Stops the requests handling process.
            The associated thread will end automatically.
        """
        self._http_server.shutdown()
        self._data_getter_thread.stop()


    def _build_device_of_type(self, d_type, ip, port, name):
        """
            Returns an instance of a specified type of remote device if its support.
            Returns None otherwise.
        """
        device = None
        if d_type in self.cfg['device_types'].keys():
            sensors = []
            for s in self.cfg['device_types'][d_type]:
                obj = s['constructor'](ip, port)
                sensors.append(obj)
            #sensors = [s['constructor'](ip, port) for s in self.remote_device_types[d_type]]
            
            device = RemoteDevice(sensors, ip, port, name, d_type)
            logging.info('Device \'%s\' of type %s created (ip: %s, port: %s)' % (device.name, d_type, device.ip, device.port))
        else:
            logging.warning('Device type not supported : %s' % d_type)

        return device


class RemoteDevice:
    """
        A remoteDevice is composed by several sensors. 
    """

    def __init__(self, sensors, ip, port, name, device_type):
        self.ip = ip
        self.port = port
        self.name = name
        self.sensors = sensors
        self.type = device_type

    def get_measures(self):
        """
            Returns a dictionary associating a measure name with its value.
            Date is included.
            {date:now, mesaure1:value, ...}
        """
        measures = {} # TODO: what if the connection is lost?
        for sensor in self.sensors:
            measures[sensor.measure_name] = sensor.get_measure()
        measures['date'] = time.time()
        return measures

    def get_sensors_by_name(self, measure_name): # TODO: Is there actualy a way that several sensors match?
        """
            Returns the sensor with the specified measure name.
            Returns a list od sensors in the case of several matches and an empty list if there's no matches.
        """
        matches = [s for s in self.sensors if s.measure_name == measure_name]
        if len(matches) == 1:
            matches = matches[0]

        return matches


class Sensor:
    def __init__(self, measure_name, measure_type, ip, port):
        """
            The measure name must be the path on which all the reaquests should be send.
        """
        self.measure_name = measure_name
        self.measure_type = measure_type
        self.ip = ip
        self.port = port

    def get_measure(self):
        """
            returns the measured value from the sensor.
        """
        
        try:
            measure = None
            str_req = 'http://' + str(self.ip) + ':' + str(self.port) + '/' + self.measure_name
            logging.debug('Request will be sent to device on %s : %s' % (self.ip, str_req))
            logging.debug('Waiting for device response...')
            response = requests.get(str_req, timeout=4) 
            time.sleep(1) # TODO  : that ensures no other requests will be sent directly after this one. Maybe a queue (kind of fifo stack) system for reqeusts would be nice here.
            measure = response.text
            logging.debug('Device %s response : %s' % (self.ip, measure))

        except requests.exceptions.ConnectionError as e:
            logging.exception('Connection with the device failed : %s' % str(e))
        except requests.exceptions.ReadTimeout as e:
            logging.exception("More than 4 seconds elapsed. We've no time to wait more!!!!")
        except Exception as e:
            logging.exception('An unexcpected exception handled during the data request for measure %s of device %s'%(self.measure_name, self.ip))
        finally:
            return measure

class InteractiveSensor(Sensor):

    def __init__(self, measure_name, measure_type, ip, port):
        
        super().__init__(measure_name, measure_type, ip, port)
        
        self.pid = PID() # Default values?

    def set_option(self, value):
        """
            Send a put request with the value to asign to the option as content.
            Returns the status code of None if it fails.
        """
        status = None
        try:
            req_str = 'http://' + str(self.ip) + ':' + str(self.port) + '/' + self.measure_name+'?value='+str(value)
            response = requests.put(req_str, data=str(value), headers={'content-type':'text/plain'}, timeout=4) 
            status = response.status_code


        except requests.exceptions.ConnectionError as e:
            logging.error('Connection with the device failed : ' + str(e))

        except requests.exceptions.ReadTimeout as e:
            logging.exception("More than 4 seconds elapsed. We've no time to wait more!!!!")
 
        except Exception as e:
            logging.exception('An unexcpected exception handled during the data request for measure %s of device %s'%(self.measure_name, self.ip))
        return status

class LocalSensor(InteractiveSensor):
    def __init__(self, measure_name, measure_type, ip, port):
        
        super().__init__(measure_name, measure_type, ip, port)
        
        self.measure_value = 0
        
    def get_measure(self):
        return self.measure_value

    def set_option(self, new_value):
        self.measure_value = new_value

