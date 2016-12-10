import Data as d
import time
import distance # For hamming distance
import random

import matplotlib.pyplot as plt
import datetime
import matplotlib.dates as mdates

if __name__ == '__main__':
    import os.path
    import logging

class HeatingProperties:
	def __init__(self, query_handler, device_name):
		"""
			Try t approach the heating time and the building properties based on the specified data.
		"""

		self.qh = query_handler
		self.device_name = device_name

		self.c1 = 1 # heating power coef
		self.c2 = 1 # heating looses coef

	def analyse(self):
		"""
			Analyse past 24h data
		"""
		raw_data = self.qh.get_measure()

		couples = [(,)]
		for couple in couples:
			Delta_T = couple[0]['temperature'] - couple[1]['temperature']
			


class PresencePredictor:
    def __init__(self, query_handler, device_name):
        self.qh = query_handler
        self.past_24_data = []
        self.data = []
        self.device_name = device_name
        self.parse_2_month()

    def _show_data(self):
        print(self.data)

    def parse_2_month(self):
        raw_pres_data = self.qh.get_last_presence(self.device_name, 60*24*3600) # List of dict [{'date':sec, 'presence':1/0}, {...}, ...] 

        time_now = time.time()

        for i in reversed(range(60)): # 60 days
            if len(self.data) <= i: # No data for day i yet
                self.data.append([])
                for j in range(96):
                    chunk_start_time = time_now - i*24*3600 - (j+1)*15*60
                    chunk_end_time = time_now - i*24*3600 - j*15*60

                    query_result = self.qh.get_measure_by_timestamp(chunk_start_time, chunk_end_time)
                    chunck = [entry['presence'] for entry in query]
                    #chunck = [measure['presence'] for measure in raw_pres_data if chunk_start_time <= measure['date'] < chunk_end_time]
                    if len(chunck):
                        #print('Nop')
                        self.data[i].append(int(sum(chunck)/len(chunck) > 0.5))
            print(self.data[i])


    
    def parse_day(self, date):
        """
            Get a list of 96 15min presence chunks
        """
        rtn = []
        start_of_day = 

        for i in range(95):
            rtn.append(self.parse_chunk(start_of_day+i*60*15, start_of_day+(i+1)*60*15))


    def parse_chunk(self, start, end):
        """
            Get the presence (bool) for a specified 15 minute interval.
        """
        rtn = None

        query_result = self.qh.get_measure_by_timestamp(chunk_start_time, chunk_end_time)
        rtn = [entry['presence'] for entry in query] # List of presence in the specified timestamp
        if len(rtn):# If there's data for the specified timestmap...
            rtn = int(sum(chunck)/len(chunck) > 0.5)
        return rtn

    def parse_past_24(self):
        """
            Get all presence data  for the past 24hours and sanythize them to build a binary vector of 96 15-min blocks.
        """
        raw_pres_data = self.qh.get_last_presence(self.device_name) # List of dict [{'date':sec, 'presence':1/0}, {...}, ...] sorted by date (mosr recent first)
        print(len(raw_pres_data))
        rtn = [0]*96 # will contain 96 cells
        j = 0 # index in raw_pres_data

        time_now = time.time()

        for i in range(96):
            chunk_start_time = time_now - (i+1)*15*60
            chunk_end_time = time_now - (i)*15*60
            # TODO: optimisation
            
            chunck = [measure['presence'] for measure in raw_pres_data if chunk_start_time <= measure['date'] < chunk_end_time]
            rtn[i] = int(sum(chunck)/len(chunck) > 0.5)
            


        return rtn

    def probability_by_time(self, t):
        """
            Returns the probability of presence in t second.
        """
        pass



#************************
#***** TESTS
#************************


def create_test_db():
    """
        Create a ThermoDB (2 tables: measure and device) with 3 columns in measure: date, device_id, presence. 
        Fill it with a device : presence_dev_1
        and presence data
    """
    # Factice
    BASIC_DEVICE_TYPES =  {
                            'presence_test':[{'measure_name':'presence', 
                                        'measure_type':'INTEGER'}]
                                        }

    # Choose db name
    db_name = 'pres_data0'
    while os.path.isfile(db_name + '.db'):
        db_name = db_name[:-1] + str(int(db_name[-1:])+1)

    # Create db with 3 columns in measure: date, device_id and presence
    print("Creation of a new database '%s.db'" %(db_name))
    TDB = d.ThermoDB(db_name + '.db', BASIC_DEVICE_TYPES)

    # Generation of 3 months of presence data
    # Start 01/01/2016
    # 1/20 probability of false data
    # each hour with +/- 30 min
    # M: [6-8]+[18-23]
    # T: [6:30-7:30]+[18-22:30]
    # W: [6-7:45]+[13-23]
    # Th: [6:15-8]+[17:23]
    # F: [7-8:45]+[23]


    current_date = 1451606400 # 01/01/2016 00:00:00
    for w in range(15): # 15 weeks
        # Monday
        start_rel_time1=6*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time1 = 8*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        start_rel_time2=18*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time2 = 23*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        for i in range(24*360): # data every 10 sec for one day
            TDB.query_handler.add_measure({'date':current_date, 'presence':int(start_rel_time1<i<end_rel_time1 or start_rel_time2<i<end_rel_time2 and bool(random.random()>0.05))}, 'presence_dev_1', commit=bool(i==24*360-1))
            current_date += 10 # Every 10 sec...

        print('Monday')
        # Thusday
        start_rel_time1=6.5*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time1 = 7.30*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        start_rel_time2=18*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time2 = 22.5*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        for i in range(24*360): # data every 10 sec for one day
            TDB.query_handler.add_measure({'date':current_date, 'presence':int(start_rel_time1<i<end_rel_time1 or start_rel_time2<i<end_rel_time2 and bool(random.random()>0.05))}, 'presence_dev_1', commit=bool(i==24*360-1))
            current_date += 10 # Every 10 sec...
        print('Tuesday')
        # Wednesday
        start_rel_time1=6.*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time1 = 7.75*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        start_rel_time2=13*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time2 = 23*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        for i in range(24*360): # data every 10 sec for one day
            TDB.query_handler.add_measure({'date':current_date, 'presence':int(start_rel_time1<i<end_rel_time1 or start_rel_time2<i<end_rel_time2 and bool(random.random()>0.05))}, 'presence_dev_1', commit=bool(i==24*360-1))
            current_date += 10 # Every 10 sec...
        print('Wednesday')

        # Thursday
        start_rel_time1=6.25*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time1 = 8*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        start_rel_time2=17*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time2 = 23*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        for i in range(24*360): # data every 10 sec for one day
            TDB.query_handler.add_measure({'date':current_date, 'presence':int(start_rel_time1<i<end_rel_time1 or start_rel_time2<i<end_rel_time2 and bool(random.random()>0.05))}, 'presence_dev_1', commit=bool(i==24*360-1))
            current_date += 10 # Every 10 sec...
        print('Thursday')

        # Friday
        start_rel_time1=7*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time1 = 8*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        start_rel_time2=23*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time2 = 23.99*360 + random.uniform(-1,0)*0.5*350 # 8h +/- 30 min
        for i in range(24*360): # data every 10 sec for one day
            TDB.query_handler.add_measure({'date':current_date, 'presence':int(start_rel_time1<i<end_rel_time1 or start_rel_time2<i<end_rel_time2 and bool(random.random()>0.05))}, 'presence_dev_1', commit=bool(i==24*360-1))
            current_date += 10 # Every 10 sec...

        print('Friday')

        # Saterday
        start_rel_time1=0*360 + random.uniform(0,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time1 = 2*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        start_rel_time2=12*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time2 = 23*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        for i in range(24*360): # data every 10 sec for one day
            TDB.query_handler.add_measure({'date':current_date, 'presence':int(start_rel_time1<i<end_rel_time1 or start_rel_time2<i<end_rel_time2 and bool(random.random()>0.05))}, 'presence_dev_1', commit=bool(i==24*360-1))
            current_date += 10 # Every 10 sec...

        print('Saterday')
        # Sunday
        start_rel_time1=6*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time1 = 8*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        start_rel_time2=18*360 + random.uniform(-1,1)*0.5*350 # 6h30 +/- 30 min
        end_rel_time2 = 23*360 + random.uniform(-1,1)*0.5*350 # 8h +/- 30 min
        for i in range(24*360): # data every 10 sec for one day
            TDB.query_handler.add_measure({'date':current_date, 'presence':int(start_rel_time1<i<end_rel_time1 or start_rel_time2<i<end_rel_time2 and bool(random.random()>0.05))}, 'presence_dev_1', commit=bool(i==24*360-1))
            current_date += 10 # Every 10 sec...

  
    
    return TDB


def show_TDB(TDB):
    raw_data = TDB.query_handler.select(['date', 'presence'], 'measure')
    dates, presences = [], []
    for entry in raw_data:
        presences.append(entry['presence'])
        dates.append(int(entry['date']))

    plt.plot(dates, presences)
    plt.show()


if __name__ == '__main__':

    logging.basicConfig(level=getattr(logging, 'WARNING', None))

    #TDB = create_test_db()
    TDB = d.ThermoDB('pres_data0.db', {'presence_test':[{'measure_name':'presence', 'measure_type':'INTEGER'}]})

    PH = PresencePredictor(TDB.query_handler, 'presence_dev_1')
    PH._show_data()



















