"""
Module used for the intelligence of the code

documentation to be found https://docs.python.org/2/library/time.html

"""

__author__ = "Denis Verstraeten"
__version__ = "0.3"


import Utils as u
import Probability as proba

import logging



class SmartControl:


	def __init__(self, thermo_measures_handler, trigger_value = 0.67):

		"""
		- trigger_value is the value (0 <= trigger_value <= 1) above the which the PID 
		will be switched on
		"""
		self.trigger_value = trigger_value
		self.thermo_measures_handler = thermo_measures_handler
		self.time_operator = u.TimeOperator(self.thermo_measures_handler)
		self.probability_model_handler = proba.ProbabilityModelHandler(self.thermo_measures_handler, self.time_operator)
				


	def run_heater(self, temp, ext_temp):
		"""
		returns a boolean that will tell if the heater needs to be switched on
		"""
		rtn = False
		if self.time_operator.get_number_of_days_since_thermostat_launch() >= 8:    #the code will a wait whole week before becoming predicitive
			t = self.time_operator.get_elapsed_seconds_since_midnight()
			delta_t = 
			rtn = self.probability_model_handler.get_probability(t + delta_t) >= self.trigger_value

		return rtn	



						






			