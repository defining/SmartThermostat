"""
This module will handle the pid controller used to regulate the temperature.
It will make a pid regulation and will also calculate and optimize the pid constants.
"""

#TO DO : documentation, conventions

__author__ = "Denis Verstraeten"
__version__ "0.1"

import Utils as u
import logging
import numpy as np



class PID:


	"""
	This class will calculate a pid controller
	"""

	def __init__(self, first_dico_measure):
		
		self.Kp = 1
		self.Ki = 1
		self.Kd = 1
		self.integral = 0
		self.valve = 0
		self.time = first_dico_measure['date']
		self.temperature = first_dico_measure['temperature']
		self.target_temp = first_dico_measure['target_temp']


	def error(self, target_temp, temperature):

		"""
		this will return the error (target_temp - current_temp)
		"""
		try:
			return target_temp - temperature

		except TypeError:
			logging.debug("Cannot calculate the error with a None value")


	def derivative(self, target_temp, temperature, date):
		
		"""
		this will return the derivative of the error
		"""
		delta_error = error(target_temp, temperature) - error(self.target_temp, self.temperature)
		delta_t = date - self.date
		return delta_error / delta_t


	def integrate(self, target_temp, temperature, date):
		
		"""
		this will return the integral of the error
		"""
		delta_t = date - self.date
		add = ((error(target_temp, temperature) + error(self.target_temp, self.temperature)) * delta_t) / 2
		self.integral += add
		return self.integral


	def pid(self, dico_measure):

		"""
		this will return a pid output value
		"""
		target_temp, temperature, date = dico_measure['target_temp'], dico_measure['temperature'], dico_measure['date']
		try:
			if target_temp != None:
				valve = int(self.Kp * error(target_temp, temperature) + self.Ki * \
					integrate(target_temp, temperature, date) + self.Kd * derivative(target_temp, temperature, date))
				if valve > 100:
					valve = 100
				elif valve < 0:
					valve = 0
			elif target_temp == None:
				valve = 0

		except TypeError:
			logging.debug("Cannot calculate the error with a None value")
			valve = self.valve
		
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


	def __init__(self, thermo_measure_handler, pid, time_operator):

		self.thermo_measure_handler = thermo_measure_handler
		self.pid = pid
		self.time_operator = time_operator


	def update_pid_constants(self):
		
		"""
		This will update the pid constants by resolving the algebric linear
		system minimizing the error
		"""

		date = self.time_operator.get_current_date()
		time_vector = self.get_time_vector(date)
		if time_vector != [] #if there was no target temp that day, the constants won't be updated

			A = [[self.a11(time_vector), self.a12(time_vector), self.a13(time_vector)],
			[self.a12(time_vector), self.a22(time_vector), self.a23(time_vector)],
			[self.a13(time_vector), self.a23(time_vector), self.a33(time_vector)]]

			B = [self.b1(time_vector), self.b2(time_vector), self.b3(time_vector)]

			constants = u.linear_equation_solver(A, b)
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
			ls.append(double_integral)

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

		for times in time_vector:
			add, value = self.double_integrate_on_a_time_vector(time_vector, value)
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
		t0 = self.get_target_temp(time_vector)

		for times in time_vector:
			add, value = self.double_integrate_on_a_time_vector(time_vector, value)
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
		list_of_dico = self.thermo_measure_handler.get_relevant_times_of_today(date)
			for dico in list_of_dico:
				rtn.append(dico['date'])
		rtn.sort()
		return rtn		


	def generate_time_vectors(self, time_vector):
		
		"""
		This will generate a vector of time vectors that will be used in the mathematical system
		"""

		rtn = []
		ls = np.split_array(time_vector, 10)
		for array in ls:
			rtn.append(list(array))

		return rtn	


	def get_error(self, t):
		"""
		returns the error at a given time
		"""

		dico = self.thermo_measure_handler.select(['temperature', 'target_temp'], 'measure', "date == '%s" % t)[0]

		return dico['target_temp'] - dico['temperature']


	def get_target_temp(self, t):
		
		"""
		returns the target temp at a given time
		"""

		return self.thermo_measure_handler.select(['target_temp'], 'measure', "date == '%s" % t)[0]['target_temp']

	def integrate_on_a_time_vector(self, time_vector):
		"""
		this will return the integral of the error on a time interval using the trapeze method
		"""

		integral = 0
		for i in range(1, len(time_vector)):
			if time_vector[i] - time_vector[i-1] < 600:
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
			if time_vector[i] - time_vector[i-1] < 600:
				i2 += ((self.get_error(time_vector[i]) + self.get_error(time_vector[i-1])) * (time_vector[i] - time_vector[i-1])) / 2
			rtn += (i2 + i1) * (time_vector[i] - time_vector[i-1]) / 2
			i1 = i2

		return rtn, i1	
					



		