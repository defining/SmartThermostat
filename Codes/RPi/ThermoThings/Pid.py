"""
This module will handle the pid controller used to regulate the temperature.
It will make a pid regulation and will also calculate and optimize the pid constants.
"""

#TO DO : documentation, conventions

__author__ = "Denis Verstraeten"
__version__ = "0.1"

import logging
import time
import matplotlib.pyplot as plt
import Utils as u
import os.path
#import Data as d


class PID:


    """
    This class will calculate a pid controller
    """

    def __init__(self):
        
        self.Kp = 4
        self.Ki = 1
        self.Kd = 0
        self.integral = 0
        self.valve = 0
        self.date = time.time()
        self.temperature = 18
        self.target_temp = 20


    def error(self, target_temp, temperature):

        """
        this will return the error (target_temp - current_temp)
        """
        try:
            return target_temp - temperature

        except TypeError:
            logging.error("Cannot calculate the error with a None value")


    def derivative(self, target_temp, temperature, date):
        
        """
        this will return the derivative of the error
        """
        delta_error = self.error(target_temp, temperature) - self.error(self.target_temp, self.temperature)
        delta_t = date - self.date 
        return delta_error / delta_t


    def integrate(self, target_temp, temperature, date):
        
        """
        this will return the integral of the error
        """
        delta_t = date - self.date
        add = ((self.error(target_temp, temperature) + self.error(self.target_temp, self.temperature)) * delta_t) / 2
        self.integral += add
        print(self.integral)
        return self.integral


    def update(self, dico_measure):

        """
        this will return a pid output value
        """
        target_temp, temperature, date = dico_measure['target_temp'], dico_measure['temperature'], dico_measure['date']
        valve = self.valve
        try:
            if target_temp != None:

                valve = int(self.Kp * self.error(target_temp, temperature) + self.Ki * \
                    self.integrate(target_temp, temperature, date) + self.Kd * self.derivative(target_temp, temperature, date))
                if valve > 100:
                    valve = 100
                elif valve < 0:
                    valve = 0
            elif target_temp == None:
                valve = 0

        except TypeError:
            
            logging.error("Cannot calculate the error with a None value")
            valve = self.valve
        except Exception as ex:
            logging.error("Unexpected error")
            logging.exception(ex)
        finally:        
            self.target_temp = target_temp
            self.temperature = temperature
            self.date = date
            self.valve = valve  
            return valve


    def set_constants(self, constants):
        """
        this will update the pid constants
        """
        self.Kp = constants[0]
        self.Ki = constants[1]
        self.Kd = constants[2]






class PIDHandler:


    """
    This class will be used to calculate the pid constants my minimizing the difference
    between the temperature and the target temperature at anytime
    """


    def __init__(self, thermo_measure_handler, pid):  #TO DO : add device_name

        self.thermo_measure_handler = thermo_measure_handler
        self.pid = pid
        #self.device_name = device_name


    def update_pid_constants(self):
        
        """
        This will update the pid constants by resolving the algebric linear
        system minimizing the error
        """

        date = u.TimeOperator.get_current_date()
        time_vector = self.get_time_vector(date)

        A = [[self.a11(time_vector), self.a12(time_vector), self.a13(time_vector)],
        [self.a12(time_vector), self.a22(time_vector), self.a23(time_vector)],
        [self.a13(time_vector), self.a23(time_vector), self.a33(time_vector)]]

        b = [self.b1(time_vector), self.b2(time_vector), self.b3(time_vector)]

        constants = u.linear_equation_solver(A, b)
        print(constants)
        self.pid.set_constants(constants)


    def a11(self, time_vector):
        
        """
        this will calculate the A11 coefficient of the matrix
        """
        time_vectors = self.generate_time_vectors(time_vector)
        rtn = 0
        ls = []
        integral = 0
        for times in time_vectors:
            integral += self.integrate_on_a_time_vector(times)
            ls.append(integral)

        for elem in ls:
            rtn += elem**2

        return rtn


    def a12(self, time_vector):
        
        """
        this will calculate the A12/A21 coefficient of the matrix
        """
        
        time_vectors = self.generate_time_vectors(time_vector)
        ls = []
        simple_integral = 0
        double_integral = 0
        value = 0
        add = 0
        for times in time_vectors:
            add , value = self.double_integrate_on_a_time_vector(times, value)
            double_integral += add
            simple_integral += self.integrate_on_a_time_vector(times)
            ls.append(double_integral * simple_integral)
        
        return sum(ls)
        


    def a13(self, time_vector):
        
        """
        this will calculate the A13/A31 coefficient of the matrix
        """

        error_t0 = self.get_error(time_vector[0])
        ls = []
        integral = 0
        time_vectors = self.generate_time_vectors(time_vector)

        for times in time_vectors:
            integral += self.integrate_on_a_time_vector(times)
            ls.append(integral * (self.get_error(times[-1]) - error_t0))

        return sum(ls)  



    def a22(self, time_vector):
        
        """
        this will calculate the A22 coefficient of the matrix
        """

        time_vectors = self.generate_time_vectors(time_vector)
        ls =[]
        rtn = 0
        integral = 0
        value = 0
        add = 0
        for times in time_vectors:
            add, value = self.double_integrate_on_a_time_vector(times, value)
            integral += add
            ls.append(integral)

        for elem in ls:
            rtn += elem**2

        return rtn  


    def a23(self, time_vector):
        
        """
        this will calculate the A23/A32 coefficient of the matrix
        """

        error_t0 = self.get_error(time_vector[0])
        ls = []
        integral = 0
        add = 0
        value = 0
        time_vectors = self.generate_time_vectors(time_vector)

        for times in time_vectors:
            add, value = self.double_integrate_on_a_time_vector(times, value)
            integral += add
            ls.append(integral * (self.get_error(times[-1]) - error_t0))

        return sum(ls)  


    def a33(self, time_vector):
        
        """
        this will calculate the A33 coefficient of the matrix
        """

        error_t0 = self.get_error(time_vector[0])
        rtn = 0
        ls = []
        time_vectors = self.generate_time_vectors(time_vector)

        for times in time_vectors:
            ls.append(self.get_error(times[-1]) - error_t0)

        for elem in ls:
            rtn += elem**2  

        return rtn


    def b1(self, time_vector):
        
        """
        this will calculate the b1 coefficient of the matrix
        """

        time_vectors = self.generate_time_vectors(time_vector)
        ls = []
        integral = 0
        target_temp = 0
        t0 = self.get_T0(time_vector)

        for times in time_vectors:
            integral += self.integrate_on_a_time_vector(times)
            target_temp = self.get_target_temp(times[-1])
            ls.append(integral * (target_temp - t0))

        return sum(ls)
        

    def b2(self, time_vector):
        

        """
        this will calculate the b2 coefficient of the matrix
        """

        time_vectors = self.generate_time_vectors(time_vector)
        ls = []
        integral = 0
        add = 0
        value = 0
        target_temp = 0
        t0 = self.get_target_temp(time_vector[0])

        for times in time_vectors:
            add, value = self.double_integrate_on_a_time_vector(times, value)
            integral += add
            target_temp = self.get_target_temp(times[-1])
            ls.append(integral * (target_temp - t0))

        return sum(ls)
        


    def b3(self, time_vector):
        
        """
        this will calculate the b3 coefficient of the matrix
        """

        time_vectors = self.generate_time_vectors(time_vector)
        ls =[]
        e0 = self.get_error(time_vector[0])
        t0 = self.get_T0(time_vector)

        for times in time_vectors:
            ls.append((self.get_error(times[-1]) - e0) * (self.get_target_temp(times[-1]) - t0))

        return sum(ls)  


    def get_T0(self, time_vector):
        
        """
        this will return the initial temperature of the dico_measure
        """
        t = time_vector[0]
        return self.thermo_measure_handler.select(['temperature'], 'measure', "date == '%s'" % t)[0]['temperature']

    def get_time_vector(self, date):

        """
        this will make a sorted list out of the dictionary of time measures
        """
        rtn = []
        list_of_dico = self.thermo_measure_handler.get_relevant_times_of_today(date)  #TO DO : add self.device_name
        for dico in list_of_dico:
            rtn.append(dico['date'])
        rtn.sort()
        return rtn      


    def generate_time_vectors(self, time_vector):
        
        """
        This will generate a vector of time vectors that will be used in the mathematical system
        """
        size = 10
        input_size = len(time_vector)
        slice_size = input_size / size
        remain = input_size % size
        result = []
        iterator = iter(time_vector)
        for i in range(size):
            result.append([])
            for j in range(int(slice_size)):
                result[i].append(iterator.__next__())
            if remain:
                result[i].append(iterator.__next__())
                remain -= 1
        return result
         


    def get_error(self, t):
        """
        returns the error at a given time
        """
        dico = self.thermo_measure_handler.select(['temperature', 'target_temp'], 'measure', "date == '%s'" % t)[0]

        return dico['target_temp'] - dico['temperature']


    def get_target_temp(self, t):
        
        """
        returns the target temp at a given time
        """
        #print(self.thermo_measure_handler.select(['target_temp'], 'measure', "date == '%s'" % t))
        return self.thermo_measure_handler.select(['target_temp'], 'measure', "date == '%s'" % t)[0]['target_temp']

    def integrate_on_a_time_vector(self, time_vector):
        """
        this will return the integral of the error on a time interval using the trapeze method
        """

        integral = 0
        for i in range(1, len(time_vector)):
            integral += ((self.get_error(time_vector[i]) + self.get_error(time_vector[i-1])) * (time_vector[i] - time_vector[i-1])) / 2

        return integral 



    def double_integrate_on_a_time_vector(self, time_vector, i_value=0):
        """
        this will return the double integral of the error on the time interval using the trapeze method twice
        """

        rtn = 0
        i1 = i_value
        i2 = i_value

        for i in range(1, len(time_vector)):
            
            i2 += ((self.get_error(time_vector[i]) + self.get_error(time_vector[i-1])) * (time_vector[i] - time_vector[i-1])) / 2
            rtn += (i2 + i1) * (time_vector[i] - time_vector[i-1]) / 2
            i1 = i2

        return rtn, i1  
                    

### TESTS ###
if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    target_temp = 20
    current_temp = 10
    outside_temp = 5
    sim_time = 0
    pid = PID()
    t_vect = [sim_time]
    temp_vect = [current_temp]
    valve_vect = [0]

    for t in range(1000):
        sim_time +=10
        t_vect.append(sim_time)
        valve = pid.update({'date':sim_time, 'temperature':current_temp, 'target_temp':target_temp})
        valve_vect.append(valve)
        current_temp += 0.7*valve - 0.2*(current_temp - outside_temp)
        temp_vect.append(current_temp)

    plt.plot(t_vect, temp_vect)
    plt.plot(t_vect, valve_vect, 'r')
    plt.show()    


"""
#Creation of a new database
BASIC_DEVICE_TYPES = {
    'pid_test':[{'measure_name':'temperature', 
    'measure_type':'REAL'}, 
    {'measure_name':'target_temp', 
    'measure_type':'REAL'}]
    
}

db_name = 'pid_data0'
while os.path.isfile(db_name + '.db'):
    db_name = db_name[:-1] + str(int(db_name[-1:])+1)

print("Creation of a new database '%s.db'" %(db_name))
TDB = d.ThermoDB(db_name + '.db', BASIC_DEVICE_TYPES)

#Launching the pid with initial constants for a cycle

target_temp = 20
current_temp = 10
outside_temp = 5
sim_time = time.time()
pid = PID()
t_vect = [sim_time]
temp_vect = [current_temp]
valve_vect = [0]
t_vect1 = [sim_time]
temp_vect1 = [current_temp]
valve_vect1 = [0]
TDB.query_handler.add_measure({'date':sim_time, 'temperature':current_temp, 'target_temp':target_temp}, 'pid_dev1')

for t in range(10000):
    sim_time += 10
    t_vect.append(sim_time)
    valve = pid.update({'date':sim_time, 'temperature':current_temp, 'target_temp':target_temp})
    valve_vect.append(valve)
    current_temp += 0.7*valve - 0.4*(current_temp - outside_temp)
    temp_vect.append(current_temp)
    TDB.query_handler.add_measure({'date':sim_time, 'temperature':current_temp, 'target_temp':target_temp}, 'pid_dev1')

#plt.plot(t_vect, temp_vect)
#plt.plot(t_vect, valve_vect, 'r')    


#finding the new constants    

PIDH = PIDHandler(TDB.query_handler, pid)
PIDH.update_pid_constants()

#plotting the updated pid controller
current_temp = 10
sim_time = t_vect[0]
for u in range(10000):
    sim_time += 10
    t_vect1.append(sim_time)
    valve = pid.update({'date':sim_time, 'temperature':current_temp, 'target_temp':target_temp})
    valve_vect1.append(valve)
    current_temp += 0.5valve - 0.1*(current_temp - outside_temp)
    temp_vect1.append(current_temp)

plt.plot(t_vect1, temp_vect1)
plt.plot(t_vect1, valve_vect1, 'r')
plt.show()    
"""


        