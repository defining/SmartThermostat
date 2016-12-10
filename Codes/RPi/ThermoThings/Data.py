"""
    Module that will be used to manage the data

    The following classes are designed to handle a database with a predifined structure that's created with:

    CREATE TABLE device ('device_id' INTEGER PRIMARY KEY, \
                                                'name' TEXT UNIQUE, \
                                                'ip' TEXT);
    CREATE TABLE measure ('measure_id' INTEGER PRIMARY KEY, \
                                                'date' INTEGER, \
                                                'temperature' REAL, \
                                                'target_temp' REAL, \
                                                'presence' INTEGER, \
                                                'valve' INTEGER)
                                                'device_id' INTEGER, FOREIGN KEY (device_id) REFERENCES device(device_id));
"""
 
__version__ = '2.0'
__author__ = 'Verstraeten Denis, Sercu Stéphane'
 

import sqlite3 as s

import logging

import os.path # For tests


# TODO: what in time?
import time

class QueryHandler:
    """
        Generic class used to handle the queries sent to a database.
    """  
    def __init__(self, db):
        self.db_path = db
        self.conn = None


    def get_cursor(self):
        try:
            if not self.conn:
                self.conn = s.connect(self.db_path)
            cur = self.conn.cursor()
        except:
            self.conn = s.connect(self.db_path)
            cur = self.conn.cursor()
        finally:
            return cur 

    def insert(self, values, table_name, commit=True):
        """
            Executes an INSERT query.

            table_name is the name of the table to be altered 
            values is a dict {'col_name':'value'}

            Returns the pk of the added row (or None if it fails to add it).

            commit indicates if the transaction must be commited and the 
            connection closed or not. Optionnal, for optimisation.
            Warning: commit to False can lead to unexpected result, 
            especially with multithreading and multiple connection!!
        """
        last_id = None # Returned value

        # Building request
        placeholders = ', '.join(values.keys())
        sql_vals = ', '.join(["'"+str(v)+"'" for v in values.values()])
        query = "INSERT INTO %s (%s) VALUES (%s)" % (table_name, placeholders, sql_vals)

        logging.debug("SQL Query to be executed in %s: \n%s\n" % (self.db_path, query))

        try:
            cursor = self.get_cursor()
            cursor.execute(query)
            last_id = cursor.lastrowid
            if commit:
                logging.debug("SQL Query commited.")
                self.conn.commit()

        except Exception as ex:
            logging.error("Exception during the execution of an INSERT query in %s\n\t \
                            values = %s\n\t table_name= %s" % (self.db_path, str(values), str(table_name)))
            logging.exception(ex)

        finally:
            if self.conn and commit:
                self.conn.close()
            return last_id



    def select(self, columns, table_name, cond='', limit=-1, group_by='', order_by=''):
        """
            Execute a SELECT request based on the specified args:
                - colums : List [col1, col2]
                - cond : string conditions
                - group_by : str columns name
                - limit : int = maximum field to return
                - order_by : str = asc / desc 
            Returns a list of dictionnaries
            [{col1:value, col2:value}, {col1:value, col2:value}]
            Returns an empty list ifno results!
            TODO : method not fully tested!
        """
        rtn = [] # Will contain the value to be returned

        conn = None # Connection to te database

        try:
            conn = s.connect(self.db_path)
            cursor = conn.cursor()

            # Building the sql request
            req_str = "SELECT %s FROM %s" % (', '.join(columns), table_name)

            if cond:
                req_str += " WHERE %s" % cond

            if group_by:
                req_str += " GROUP BY %s" % group_by

            if order_by:
                req_str += " ORDER BY %s DESC" % order_by

            if limit:
                req_str += " LIMIT %s" % str(limit)

            logging.debug("SQL Query to be executed in %s: \n%s\n" % (self.db_path, req_str))
            
            sql = cursor.execute(req_str)
            ls = sql.fetchall() # Returns a list of tuple [(t1,),(t2,),...]
            

            # Data formatting
            rtn = []
            for tup in ls:
                rtn.append({})
                for i in range(len(tup)):
                    rtn[-1:][0][columns[i]] = tup[i]

        except Exception as ex:
            logging.error("Exception during the execution of an SELECT query \
                            in %s\n\t table_name= %s" % (self.db_path, str(table_name)))
            logging.exception(ex)
        finally:
            if conn:
                conn.close
            return rtn


class ThermoMeasureHandler(QueryHandler):
    """
        This class serves and updates all the data from the ThermoServer.
        This class suposes that the structure of the database is a valid ThermoDB structure.
    """

    def __init__(self, db_path, measure_table_name, device_table_name, measure_col_names, device_col_names):
        super(ThermoMeasureHandler, self).__init__(db_path)
        self.db_path = db_path
        self.measure_table_name = measure_table_name
        self.device_table_name = device_table_name
        self.device_col_names = device_col_names
        self.measure_col_names = measure_col_names

    # ******
    # Measure manipulation
    # ******
    def add_measure(self, measures, device_name, commit=True):
        """
            Add measures related to a device.
        """
        # SELECT device_id FROM device WHERE name='device_name'
        sql_device_match = self.get_device_by_name(device_name)

        if sql_device_match: # If martch
            device_id = sql_device_match['device_id']
        else:   # No match
            device_id = self.register_device(device_name)
            logging.info("Addition of measures related to a unregistered device was \
                            attemped. %s device was added." % device_name)
            

        measures['device_id'] = device_id
        measure_id = self.insert(measures, self.measure_table_name, commit=commit)
        if measure_id:
            logging.debug("New measures were added in the database :\n\t \
                            measures= %s\n\tdevice_name='%s'"%(str(measures), device_name))
        else:
            logging.error("Addition of measures in the database failed :\n\t \
                            measures= %s\n\tdevice_name='%s'"%(str(measures), device_name))


    def save_measure_of_all_devices(self, measures):
        """
        saves the measures of each remote devices connected to the system into the 
        database.
        measure is a dictionary : - keys : remote devices names
                                  - values : the measures of all the sensors of the 
                                  remote device
        """ 
        for device_name in measures.keys():
            sql_device_match = self.get_device_by_name(device_name)
            if sql_device_match:
                device_id = sql_device_match['device_id']
            else:
                device_id = self.register_device(device_name)
                logging.info("Addition of measures related to a unregistered device \
                                was attemped. %s device was added." % device_name)

            self.add_measure(measures[device_name], device_name)
            logging.debug("New measures added for '%s'." % device_name)
    
    def get_measure(self, where=1):
        """
            Gets measure where...
        """
        return self.select(self.measure_col_names, 'measure', where)

    def get_measure_by_timestamp(self, start, end):
        """
            returns measures that were collected in the specified tiùestmp
        """
        return self.get_measure('date > %s AND date < %s'%(str(start), str(end)))

    def get_measures_by_day(self, day, n_limit=-1, date_limit=2000000000):
        """
            Returns the entries which were saved on a specified weekday.
            day: 0-6
            n_limit (int) : the maximum number of entries to return
            date_limit (int): the dte of the oldest entry to retrieve

            TODO: return 'device_id' or directly its name? Anyway it can be retrieved using get_device_by_id
        """
        COLS = ['date', 'temperature', 'presence', 'valve', 'device_id']
        FROM = 'measure'
        WHERE = "strftime('%w', date(date, 'unixepoch'))=='"+str(day)+"' AND date < " + str(date_limit)

        return self.select(COLS, FROM, WHERE, n_limit)


    def get_last_presence(self, max_time=24*3600):
        """
            Return a list of dict [{'date':sec, 'presence':1/0}, {...}, ...] 
            containing presence data for the past 'max_time' seconds 
            and for the specified device.
        """
        WHERE = "date > "+str(time.time()-max_time)+ " AND date <= " + str(time.time())
        return self.select(['date', 'presence'], 'measure', WHERE, order_by='date')

    def get_date_of_first_entry(self, device_name):
        """
            returns the epoch date of the first entry in the measure table
            this will be used in a method from the Smart Control
        """
        return self.select(['date'], 'measure', "measure_id=1")[date]



    def get_presence_by_day_and_by_time_interval(self, day, time_min, time_max, device_name, n_limit=150, date_limit=2000000000):
        """
            Returns all the presence measures when measures were taken on a specified a specified day
            in this time interval.
            day: 0=Sunday, 6=Saturday
            time = edges of the time interval in seconds
            n_limit (int) : the maximum number of entries to return
            date_limit (int): the dte of the oldest entry to retrieve
        """   
        COLS = ['presence']
        FROM = 'measure'
        WHERE = "strftime('%w', date(date, 'unixepoch'))== '" + str(day) + "' AND \
         date - strftime('%s', date(date, 'unixepoch', 'start of day')) >= " + str(time_min) + " AND \
         date - strftime('%s', date(date, 'unixepoch', 'start of day')) <= " + str(time_max) + " AND \
         presence != 'NULL' AND date < " + str(date_limit) + " AND device.name == " + str(device_name)

        return self.select(COLS, FROM, WHERE, n_limit)


    def get_relevant_times_of_today(self, today, device_name, n_limit=-1, date_limit=2000000000):
        """
            Returns all the measures of a day 
            today is a string formatted to match the sqlite function
            date(date)
        """
        COLS = ['date']
        FROM = 'measure'
        WHERE = "date(date) == '" + today + "' AND \
        target_temp != 'NULL' AND temperature != 'NULL' AND date < " + str(date_limit)

        return self.select(COLS, FROM, WHERE, n_limit)
          

    # ******
    # Device manipulation
    # ******

    def register_device(self, device_name, ip=''):
        """
            Add a new device with the specified name (and ip) in the database.
        """
        device_id = self.insert({'name':device_name, 'ip':ip}, 'device')
        if not device_id: # That means it failed to add it in the database
            logging.warning("ThermoMeasureHandler failled to register a new \
                                device (%s)" % device_name)

        return device_id


    def get_device_where(self, where):
        """
            Return a dictionnary with 3 keys (the three columns in the 
            database) : 'device_id', 'name' and 'ip', containing the 
            data about the device matching the specified condition (where)
        """
        # SELECT device_id, name, ip FROM device WHERE where
        matching_devices = self.select(['device_id', 'name', 'ip'], 'device', where)
        if matching_devices:
            rtn = matching_devices[0] # Normally, only one matches, anywayn the first match is returned.
        else:
            rtn = None
        return rtn

    def get_device_by_id(self, d_id):
        """
            Returns a dictionnary with 3 keys (the three columns in the 
            database) : 'device_id', 'name' and 'ip'.
        """
        # SELECT device_id, name, ip FROM device WHERE id='d_id'
        return self.get_device_where("id='%s'"%d_id)
        

    def get_device_by_name(self, d_name):
        # SELECT device_id, name, ip FROM device WHERE name='d_name'
        return self.get_device_where("name='%s'"%d_name)



class ThermoDB:
    """
        Creates a new database (or loads an existing one) dedicated to 
        the storage of the data from ThermoServer.

        Adds (if they don't already exist) two tables : measures and 
        devices, and generates a QueryHandler that will be used to access and 
        update the data.


        A valid structure for a database managed
    """

    def __init__(self, db_path, device_types, measure_table_name='measure', device_table_name='device'):
        """
            Creates a new database at the specified path. 
            Adds a measure table. Each columns will be a measure name 
            specified in the device_types.

            device_types = {'type_name':{'measure_name':'measure_type'}}

            If this database already exists, checks if its structure 
            matches the specfied one. 
            It must contain 2 tables : measure and device. If so, nothing 
            is changed and the data will be appended, else, a new database 
            with a valid structure is created.
        """
        self.db_path = db_path
        self.measure_table_name = measure_table_name
        self.device_table_name = device_table_name

        self.query_handler = None

        try:

            conn = s.connect(self.db_path)

            existing_tables = self._get_table_names(conn)

            if len(existing_tables) == 0: # Database didn't exist.
                self.create_tables(conn, device_types)
                logging.debug("Database created at %s" % self.db_path)

            elif 'device' in existing_tables and 'measure' in existing_tables: # Database exists and has the two required tables
                logging.debug("A valid ThermoDB already exists at %s" % db_path)

                existing_cols = self._get_cols(conn, 'measure')
                specified_cols = self._get_cols_from_device_types(device_types)

                req_alter_str = ''
                cursor = conn.cursor()
                for col_name, col_type in specified_cols.items(): # Checks if all the needed columns already exist
                    if not col_name in existing_cols.keys():
                        req_alter_str += "ALTER TABLE measure ADD COLUMN %s %s;" % (col_name, col_type)
                        cursor.execute(req_alter_str)
                        logging.debug("Column %s of type %s added to measure." % (col_name, col_type))

                conn.commit()

            else:
                logging.error("A file named %s already exists but isn't a valid ThermoDB." % db_path)
                raise Excpetion("Not valid ThermoDB")
                pass # TODO; what if a db already exists at db_path but isn't a valid ThermoDB?
                # Delete it and create a new one? Create a new one with another name?

            measure_col_names = self._get_cols(conn, 'measure')
            device_col_names = self._get_cols(conn, 'device')
            self.query_handler = ThermoMeasureHandler(self.db_path, self.measure_table_name, self.device_table_name, measure_col_names, device_col_names)

        except Exception as ex:
            logging.exception(ex)


    def create_tables(self, conn, device_types):
        """
            Adds 2 new tables (measure and device) to the specified database 
            (specified by a connection).
            The columns of the 'measure' table will be generated based on 
            the supported types of reomoteDevice: 
            device_types = {'type_name':[{'measure_name':'temp', 'measure_type':'REAL', 'constructor':func}, ...]}
        """
        
        # Device
        req_str_device = "CREATE TABLE device ('device_id' INTEGER PRIMARY KEY, \
                                                'name' TEXT, \
                                                'ip' TEXT);"

        # Measure
        cols = self._get_cols_from_device_types(device_types)
        req_str_measure = "CREATE TABLE measure ('measure_id' INTEGER PRIMARY KEY, 'date' INTEGER"

        for col_name, col_type in cols.items():
            req_str_measure += ", '%s' %s" % (col_name, col_type)

        req_str_measure += ", 'device_id' INTEGER, FOREIGN KEY (device_id) REFERENCES device(device_id));"
        
        # Execution
        cursor = conn.cursor()
        cursor.execute(req_str_device)
        logging.debug("Device table added : \n %s" % req_str_device)
        cursor.execute(req_str_measure)
        logging.debug("Measure table added : \n %s" % req_str_measure)
        conn.commit()



    def _get_cols_from_device_types(self, device_types):
        """
            transforms 
            device_types = {'type_name':[{'measure_name':'temp', 'measure_type':'REAL', 'constructor':func}, ...]}
            to
            {'measure_name':'measure_type'}

            Note: 2 devices can have same measure_name (same sensor). 
            This method prevent having 2 same columns.
        """
        cols = {}
        for dev_type_name, measures in device_types.items():
            for measure in measures:
                if not measure['measure_name'] in cols.keys():
                    cols[measure['measure_name']] = measure['measure_type']
            
        return cols

    def _get_table_names(self, conn):
        """
            Returns a list of the names of the tables
            contained in the database specified by the connection passed 
            as arg.
        """
        
        tables = []

        cursor = conn.cursor()
        req_str = "SELECT name FROM sqlite_master WHERE type='table';"
        sql = cursor.execute(req_str)
        ls = sql.fetchall() # Returns a list of tuple [(t1,),(t2,),...]
        
        return [t[0] for t in ls]


    def _get_cols(self, conn, table_name):
        """
            Returns a Dict {'col_name':'col_type', 'col_name':'col_type',...}
        """
        cursor = conn.cursor()
        req_str = "PRAGMA table_info(%s)" % table_name
        sql = cursor.execute(req_str)
        ls = sql.fetchall() # [(0, 't_name', 'TYPE', ., ., .)]

        cols = {}
        for col in ls:
            cols[col[1]] = col[2]

        return cols




def test_db_creation():
    """
        Tests the cration (and recuperation) of a ThermoDB
        1) Test for normal ThermoDB construction (no existing db)
        2) Test what append if a valid ThermoDB already exist and contain all the needed columns in the measure table
        3) Test what append if some of the needed columns doesn't exist. Are they correctly added?

        Returns the created ThermoDB object.
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

    # TEST 1: Normal ThermoDB construction

    # We absolutely want to create a new database, the db name must not exisst!
    db_name = 'data0'
    while os.path.isfile(db_name + '.db'):
        db_name = db_name[:-1] + str(int(db_name[-1:])+1)

    print("Creation of a new database '%s.db'" %(db_name))
    TDB = ThermoDB(db_name + '.db', BASIC_DEVICE_TYPES)
    print("You can check that the database have been correctly created with \n\t\
                sqlite3 \n\t\
                .open %s.db\n\t\
                .tables \n\t\
                PRAGMA table_info(measure) \n\t\
            This should show you the 2 tables 'measure' and 'device' and 3 columns \n\t\
            for the measure tables 'id', 'date', 'temperature', 'presence' and 'valve'."%db_name)

    


    # TEST 2: ThermoDB loading from an existing one
    print("\n\n\nLet's try to create a new instance of ThermoDB based on the existing \n\t\
            database (%s.db) with the same supported device types (thus the same \n\t\
            needed columns in the measure table." % db_name)

    TDB2 = ThermoDB(db_name + '.db', BASIC_DEVICE_TYPES)



    # TEST 3: ThermoDB loaded from an existing one and new columns are added
    print("""\n\n\nLet's try to reuse the same database with one more supported device type 'humidity' (type REAL)""")
    device_types = BASIC_DEVICE_TYPES
    device_types['new_thin'] = [{'measure_name':'humidity', 
                                        'measure_type':'REAL', 
                                        'constructor':lambda *args: Sensor('humidity', 'REAL', *args)}
                                    ]

    TDB3 = ThermoDB(db_name + '.db', device_types)


    # TDB2 is the database with the default suported types
    return TDB2


def test_device_getting_data(TDB):
    """
        Add some data in the a newly created ThermoDB and test 
        if the retrievial functions work correctly.
    """
    QH = TDB.query_handler

    print("trying to insert {'name':'test1', 'ip':'127.0.0.1'} to the device_table")
    QH.register_device('test1','127.0.0.1')

    print("trying t get this data back")
    print('"Manually"...')
    print(QH.select(['name', 'ip'], 'device'))
    print('Using the specific method "get_device_by_name"...')
    print(QH.get_device_by_name('test1'))

def test_measure_getting_data(TDB):
    """
        Adds...
    """
    QH = TDB.query_handler

    # We specify a device that doesn't exists
    QH.add_measure({'temperature':'32.2', 'date':time.time()}, 'device0')

    # Now it exists
    QH.add_measure({'temperature':'31.2', 'date':time.time()}, 'device0')

    print('\n\nTest date')
    print(QH.get_measures_by_day('2'))

def test_devices_measures_saving(TDB):
    """
        Tests the save_measure_of_all_devices method.
    """
    data = {'device0':{'temperature':'32.0', 'presence':'1', 'date':'3000000'}, 'device1':{'temperature':'33.0'}}
    TDB.query_handler.save_measure_of_all_devices(data)

if __name__ == '__main__':
    logging.basicConfig(level=getattr(logging, 'DEBUG', None))
    TDB = test_db_creation()
    test_device_getting_data(TDB)
    test_measure_getting_data(TDB)
    test_devices_measures_saving(TDB)


