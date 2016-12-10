"""
Module that will be used to deal with the probability

The modelisation idea used in this code consists in minimizing the difference between a probability function
of the time (p(t)) and the actual probability measures. This will be executed frequently (e.g. : daily) and 
will optimize the efficiency and the accuracy of the prediction model.

documentation to be found https://docs.python.org/2/library/time.html

"""

__author__ = "Denis Verstraeten"
__version__ = "1.0"

from Utils.Utils import TimeOperator
from .Data import ThermoDB  # For tests
import logging
import os.path # For tests
import time # For tests
#import matplotlib.pyplot as plt # To show graphics


def linear_equation_solver(A, b):
    """
    returns the solved vector x coming from Ax=b
    """
    A = np.array(A)
    b = np.array(b)
    return list(np.linalg.solve(A, b))  

class HeatingPropertiyModel:
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

        #couples = [(,)]
        #for couple in couples:
        #    Delta_T = couple[0]['temperature'] - couple[1]['temperature']
            



class ProbabilityModel:


    """
    This class will handle the mathematical equation
    """
    def __init__(self, day):
        self.day = day
        self.A = 1
        self.B = 1
        self.C = 1
        self.D = 1
        self.E = 1
        self.F = 1


    def probability_model(self,t):
        """
        the probability function will be modelized with a polynomial function of the 
        fifth degre to guarantee a correct interpolation
        """
        rtn = self.A*(t**5) + self.B*(t**4) + self.C*(t**3) + self.D*(t**2) + self.E*t + self.F
        if rtn >= 1:
            rtn = 1
        elif rtn <= 0:
            rtn = 0 
        return rtn


    def set_constants(self, constants):
        """
        sets the value of the constants
        """
        self.A = constants[0]
        self.B = constants[1]
        self.C = constants[2]
        self.D = constants[3]
        self.E = constants[4]
        self.F = constants[5]



class ProbabilityModelHandler:
    


    """
    This class will handle everything that needs to be done on the probability model
    """

    def __init__(self, thermo_measures_handler, device_name):

        self.list_of_probability_model = [ProbabilityModel(i) for i in range(7)]    
        self.thermo_measures_handler = thermo_measures_handler
        self.time_vector_discrete = [i*15*60 for i in range(96)]
        self.time_vector_continuous = [i for i in range(86400)]

        
    def update_probality_model(self, day=None):
        """
        this will update the constants to make the model fit the reality better
        """
        if day == None:
            day = TimeOperator.get_current_day() # Today by default
        A = []
        b = [None]*6
        t = self.time_vector_discrete

        for i in range(6):
            A.append([])
            b[i] = self.coef_b(5-i, t, day)
            for j in range(6):

                A[i].append(self.coef_a(10-i-j, t))   #those lines are creating the matrixes
                     
        constants = linear_equation_solver(A, b)
        self.list_of_probability_model[day].set_constants(constants)    
    


    def get_probability(self, t):
        """
        returns the probability at a given time
        """
        day = self.time_operator.get_current_day()
        if t > 86400:
            t = t % 86400
            day = self.time_operator.increment_day(day)

        return self.list_of_probability_model[day].probability_model(t) 


    def measured_probability(self, day, t):
        """
        returns the measured probability of presence at a given time of a day
        """
        t_min = t
        t_max = t + 15*60 - 1
        list_of_presence_dico = self.thermo_measures_handler.get_presence_by_day_and_by_time_interval(day, t_min, t_max, device_name)
        return self.probability_ratio(list_of_presence_dico)


    def probability_ratio(self, ls):
        """
        returns the ratio of the number of observed presence
        on a given time
        """
        N = len(ls)
        n = 0
        for dico in ls:
            n += dico['presence']

        return n/N  

        
    def coef_a(self, j, ls):
        """
        function used to simplify the mathematical expression used in the update model
        """
        rtn = 0
        for elem in ls:
            rtn += elem**j
        return rtn


    def coef_b(self, r, ls, day):
        """
        function used to simplify the mathematical expression used in the update model
        """
        rtn = 0
        for elem in ls:
            rtn += self.measured_probability(day, elem)*(elem**r)
        return rtn    


#************************
#***** TESTS
#************************

def create_test_db():
    # Factice
    BASIC_DEVICE_TYPES =  {
                            'presence_test':[{'measure_name':'presence', 
                                        'measure_type':'INTEGER'}]
                                        }

    # Chose db name
    db_name = 'pres_data0'
    while os.path.isfile(db_name + '.db'):
        db_name = db_name[:-1] + str(int(db_name[-1:])+1)

    # Create db with 3 columns in measure: date, device_id and presence
    print("Creation of a new database '%s.db'" %(db_name))
    TDB = ThermoDB(db_name + '.db', BASIC_DEVICE_TYPES)

    # Add 1000 entries in table 'measure'
    for i in range(48*360):
        # Interval of 10 sec between two enties
        # No presence for the first 2000 sec, presence for the 6000 next sec and again no pressence for the 2000 last seconds.
        TDB.query_handler.add_measure({'date':24*3600+time.time()-10*i, 'presence':int(1)}, 'presence_dev_1')

    return TDB

if __name__ == '__main__':
    BASIC_DEVICE_TYPES =  {
                            'presence_test':[{'measure_name':'presence', 
                                        'measure_type':'INTEGER'}]
                                        }


    logging.basicConfig(level=getattr(logging, 'WARNING', None))
    #TDB = create_test_db() # Return a ThermoDB with a model of presence
    TDB = ThermoDB('pres_data0.db', BASIC_DEVICE_TYPES)

    PMH = ProbabilityModelHandler(TDB.query_handler)
    PMH.update_probality_model()

    #print(PMH.get_probability(300))

    y = [PMH.get_probability(t) for t in PMH.time_vector_continuous]

    #plt.plot(PMH.time_vector_continuous, y)
    #plt.show()


