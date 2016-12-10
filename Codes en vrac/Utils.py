#!/usr/bin/env python3

"""
    This module contains some usefull classes for the ThermoServer
    and for the Smart prediction
"""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import logging # used in RequestRouter, TODO: better way to implemend logging in an undependent module?
import requests
import unittest
import numpy as np
import time
import Data as d

# Only for tests


if __name__ == '__main__':
    from ProtocolTester import ThermometerServer
    from ProtocolTester import ThinThermostatServer



class RepeatingTimer(threading.Timer):
    """
        Call a function periodically (following a specified interval) in a new thread.
        The thread is started by Timer's start method.
    """
    def __init__(self, interval, function, max_=0, *args, **kwargs):
        """
            interval is the period (in sec.) between two call of function(*args, **kwargs)
            you can specify a 'max' parameter that limit the number of execution of function (0 for unlimited)
        """
        self.reapeatingFunction = function
        self.max = max_
        self.i = 0 # number of times that function has already been executed
        super(RepeatingTimer, self).__init__(interval, self.repeat, args, kwargs)
        

    def repeat(self, *args, **kwargs):
        self.reapeatingFunction(*self.args, **self.kwargs)
        self.i += int(bool(self.max))
        if not self.max or self.i <= self.max-1:
            self.run()

    def stop(self):
        self.cancel()



class RequestRouter(BaseHTTPRequestHandler):
    """
    Handles http request and callbacks the specified function. 
    It only can respond with an http code (no content).
    """
    def __init__(self, routes, *args):
        self.routes = routes # Contains the associaton path => callback, a callback must return a response code, 200 will automatically returned otherwise
        super().__init__(*args)

    def do_PUT(self):
        """
            Method called every time a PUT request is handled.
            It will try to route the request to the correct callback
        """
        self._route('PUT', self.path)


    def do_GET(self):
        """
            Method called every time a GET request is handled.
            It will try to route the request to the correct callback
        """
        self._route('GET', self.path)

    def do_POST(self):
        """
            Method called every time a POST request is handled.
            It will try to route the request to the correct callback
        """
        self._route('POST', self.path)

    


    def _route(self, method, path):
        """
            Associates a (method/path) to callbacks or send an eror code if it fails.
        """
        if method in self.routes.keys(): # If supported method
            if path not in self.routes[method].keys(): # if path not supported...
                path = '*'  # default callback
            if path in self.routes[method].keys(): # if supported path (or default callback)
                content = ''
                if 'Content-Length' in self.headers:
                    content = self.rfile.read(int(self.headers['Content-Length']))
                request_data = {'headers':self.headers.items(), 
                                'content':content}
                http_code = self.routes[method][path](request_data)
                logging.debug('A supported request have been handled. Produced result : ' + str(http_code))
                if http_code == None or type(http_code) is not int: # TODO: better check if it's an http status code than just if it's a number...s
                    http_code = 501 # Not implemented
                    logging.debug('The produced result isn\'t a valid http code. 501 will be sent')
                self._send_code(http_code)

            else:
                logging.debug('A request with a non supported path have been handled. 404 will be send.')
                self._send_code(404) # Not found

        else:
            logging.debug('A request with a non supported method have been handled. 503 will be send.')
            self._send_code(503) # Service unavaliable


    def _send_code(self, code):
        self.send_response(code)
        self.end_headers()


    def log_message(self, format, *args):
        """
            Overides the log_message method from BaseHTTPRequestHandler 
            to prevent stdout at every connection.
            TODO : A log system may be implemented later.
        """
        return




# ********
# Testing RequestRouter
# ********

class TestRequestRouter(unittest.TestCase):
    """
        Tests the RequestRouter class.
        Tests that this class that correctly handle 3 types of 
        request : GET, POST and PUT, and that it cas also routes 
        those requests to the specified callback.
    """

    @classmethod
    def setUpClass(cls):
        """
            Runned at the start of the TestCase.
            Sets up a generic HTTPServer with a RequestRouter as RequestHandlerClass 
            and transmits all the routes needed for thes following tests.
        """
        cls.routes = {'PUT':{'/puttest':cls.PUT_callback}, 'GET':{'/gettest':cls.GET_callback, '/callbackfailtest':cls.FAIL_callback}, 'POST':{'/posttest':cls.POST_callback}}

        server_address = ('localhost', 8081)

        handler_class = lambda *args: RequestRouter(cls.routes, *args)
            
        cls._http_server = HTTPServer(server_address, handler_class)


        print("Starting test server on port 8081...")
        threading.Thread(None, cls._http_server.serve_forever, 'RequestHandlingThread').start()
        print('Server started.\n')


    @classmethod
    def tearDownClass(cls):
        print('Server stopping...')
        cls._http_server.shutdown()
        print('Server stopped')


    # These functions are the callbacks that will be used by the RequestRouter class.
    def PUT_callback(request_data):
        return 200

    def GET_callback(request_data):
        return 200

    def POST_callback(request_data):
        return 200

    def FAIL_callback(request_data):
        return 'not a http code'

    def default_callback(self, request_data):
        return 201 # Random http status code just for testing

    # Does it handle correctly the GET, POST, PUT request on supported path?
    def test_sup_PUT(self):
        print('testing PUT callback on supported path...')
        expected_response_code = 200
        self.assertEqual(requests.put('http://localhost:8081/puttest', 'content').status_code, expected_response_code)

    def test_sup_GET(self):
        print('testing GET callback on supported path...')
        expected_response_code = 200
        self.assertEqual(requests.get('http://localhost:8081/gettest').status_code, expected_response_code)

    def test_sup_POST(self):
        print('testing POST callback on supported path...')
        expected_response_code = 200
        self.assertEqual(requests.post('http://localhost:8081/posttest').status_code, expected_response_code)

    # What if the path is not supported?
    def test_unsup_PUT(self):
        print('testing PUT callback on unsupported path...')
        expected_response_code = 404
        self.assertEqual(requests.put('http://localhost:8081/unsupported', 'content').status_code, expected_response_code)

    def test_unsup_GET(self):
        print('testing GET callback on unsupported path...')
        expected_response_code = 404
        self.assertEqual(requests.get('http://localhost:8081/unsupported').status_code, expected_response_code)

    def test_unsup_POST(self):
        print('testing POST callback on unsupported path...')
        expected_response_code = 404
        self.assertEqual(requests.post('http://localhost:8081/unsupported', {'param':'value'}).status_code, expected_response_code)

    # Test the default (*) route
    def test_default_route(self):
        print('testing GET default (*) callback...')
        self.routes['GET']['*'] = self.default_callback 
        expected_response_code = 201
        returned_response_code = requests.get('http://localhost:8081/unsupported', {'param':'value'}).status_code
        del self.routes['GET']['*']
        self.assertEqual(returned_response_code, expected_response_code)
        

    # What if the callback does not return any http code?
    def test_default_code(self):
        print('testing the http code return by default...')
        expected_response_code = 501
        self.assertEqual(requests.get('http://localhost:8081/callbackfailtest').status_code, expected_response_code)


def tests():

    logging.basicConfig(level=logging.DEBUG)


    print('Testing the RepeatingTimer class')
    print('='*60 + '\n')
    print('The following stdout should be 3 "Hello world", each with 1 sec of interval')
    fn = lambda:print('Hello World')
    t = RepeatingTimer(1, fn, 3)
    t.start()
    time.sleep(4)


    print('\n\nTesting the RequestRouter class')
    print('='*60 + '\n')
    unittest.main()

if __name__ == '__main__':
    tests()



class TimeOperator:
    """
    This class will posses the methods that will make operations on time
    """   


    def __init__(self, thermo_measures_handler):
        
        self.thermo_measures_handler = thermo_measures_handler

        

    def get_elapsed_seconds_since_midnight(self):
        """
        returns the number of seconds elapsed since the beginning of the day
        """ 
        t = time.gmtime(time.time())
        return int(strftime('%H', t))*3600 + int(strftime('%M', t))*60 + int(strftime('%S', t))


    def get_elapsed_days_since_epoch(self, t):
        """
        returns the number of days elapsed since epoch time
        """
        return t//(24*60*60)


    def get_number_of_days_since_thermostat_launch(self):
        """
        returns the number of days since thermostat was launched 
        """
        t = self.thermo_measures_handler.get_date_of_first_entry()
        return get_elapsed_days_since_epoch(time.time()) - get_elapsed_days_since_epoch(t)    
    

    def get_current_day(self):
        """
        returns the current day
        """
        return int(time.strftime('%w', time.gmtime(time.time())))


    def increment_day(self, day):
        """
        this will increment a day value in a correct way
        """ 
        if day == 6:
            day = 0
        else:
            day += 1

        return day    


    def get_current_date(self):
        """
        returns the epoch time
        """              
        return strftime("%Y-%m-%d", time.gmtime())


#*****************************
#          FUNCTIONS         *
#*****************************

def linear_equation_solver(A, b):
    """
    returns the solved vector x coming from Ax=b
    """
    A = np.array(A)
    b = np.array(b)
    return list(np.linalg.solve(A, b))  







    