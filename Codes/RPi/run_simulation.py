#import argarse
import xml.etree.ElementTree as ET      # For cfg file parsing purpose


from Simulators.ThermometerServer import ThermometerServer
from Simulators.ThinThermostatServer import ThinThermostatServer

from Utils import Utils as u

from datetime import datetime

#parser = argparse.ArgumentParser()


"""parser.add_argument("--cfg-file",
					help="An xml configuration file path used to parameter the simulation",
					default="")"""

#args = parser.parse_args()


class ThermoSim:
	"""
		A Simulation is made of 2 remote devices simulating real values for temperatures and presence.
		A remote device type 'outside' is simulating the outside temperature. 
			The initial outside temperature and its variation can be specified in the SimConfig file. 
			This temperature affects the variation of the "inside" temperature

		A remote device of type 'thin' that simulate the variation of temperature and presence. 
			The inside temperature is calculated using a specified method and can depend of the outside temperature and the opening of valve.
			The presence can change following a specified rule.

		Those two remote device can communicate with a server exactly like real ones. (Established communication protocol)

		The data (temperatures/presence/valve) are update each time the valve
	"""

	def __init__(self, cfg_path='thermoSim.cfg'):
		"""
			Use the specified configuration file to initialize the simulation
		"""
		self.config = SimConfig(cfg_path)

		self.outside = ThermometerServer(init_temp=self.config.init_out_temp, port=9001)
		self.thin = ThinThermostatServer(init_temp=self.config.init_temp, port=9002)

		self._data_updater_thread = u.RepeatingTimer(self.config.period, self.update_all)
	def connect_to_server(self):
		"""
			Connects the 2 devices to the server
		"""
		self.outside.start()
		self.outside.register(self.config.server_ip, self.config.server_port)

		self.thin.start()
		self.thin.register(self.config.server_ip, self.config.server_port)


	def run(self):
		"""
			Run the simulation. The devices are going to connect to the server, 
			the tempeartures, presence will start to variate and the those 
			informations will be accessible to the server.
		"""
		self._data_updater_thread.start()
		f = open('output.csv', 'w') #TODO: handle output file correctly (cfg)
		f.write('(datetime;valve;thin_temp;thin_pres;out_temp)\n')
		f.close()

	def save_state(self):
		"""
			Save the current state of the simulation in a file (csv fomrat)
			# TODO: Efficiency optimisation: open/close...
		"""
		f = open('output.csv', 'a')
		state = ';'.join([str(datetime.now()), str(self.thin._actuation_value), str(self.thin.temperature), str(self.thin.presence), str(self.outside.temperature)])
		print(state)
		f.write(state + '\n')
		f.close()


	def update_out_temp(self):
		"""
			Update the outside temperature
		"""
		pass # Constant for now


	def update_presence(self):
		"""
			Update presence in function of specified presence model.
		"""
		if self.config.presence_model == 'permanent':
			self.thin.presence = 'true'

	def update_temp(self):
		"""
			Update the inside temperature (tempearture returned by the thin).
			The temperature increase with the valve and decrease with the difference 
			beetween the inside temperature and the outside tempearture. So if the
			valve is set to 0 and the inside tempearture = outside temp, the inside 
			tempearture remains the same.
		"""
		current_temp = self.thin.temperature
		outside_temp = self.outside.temperature
		self.thin.temperature = current_temp + 0.01*self.config.valve_coef*self.thin._actuation_value - self.config.out_temp_coef*(current_temp - outside_temp)

	def update_all(self):
		# 1) Update the inside temp (function of valve and outside temp)
		self.update_temp()

		# 2) Update the outside temp (function of out_temp_coef)
		self.update_out_temp()

		# 3) Update presence
		self.update_presence()

		# 4) Save current state
		self.save_state()


class SimConfig:
	DEFAULT = {'server_port':8080, 
				'server_ip':'localhost', 
				'target_temp':30, 
				'init_out_temp':10, 
				'init_temp':10, 
				'valve_coef': 1,
				'out_temp_coef': 0.1,
				'temp_model':'linear', 
				'presence_model':'permanent',
				'period':1}

	VALID_TEMP_MODEL = ('constant', 'random')
	VALID_PRESENCE_MODEL = ('periodic', 'random', 'permanent')


	"""
		The configuration file can define those paramters: 

		temp_model : The method used to simulate the temperature variation. Valid values are specified in VALID_TEMP_MODEL.
		presence_model : The method used to simulate the presence variation. Valid values are specified in VALID_PRESENCE_MODEL.
		target_temp : A single temperature (real value) that is targeted during the simulation. In real case, this temperature may change with time, this can be simulated with several simulations.
	"""
	def __init__(self, cfg_path):
		"""
			cfg_path is the path of the xml configuration file
		"""
		self.cfg_path = cfg_path
		self.cfg_root = self.load_cfg(self.cfg_path)
		"""
		self.target_temp = self.parse_target_temp(self.DEFAULT['target_temp'])
		self.temp_model = self.parse_temp_model(self.DEFAULT['temp_model'])
		self.presence_model = self.parse_presence_model(self.DEFAULT['presence_model'])
		self.init_out_temp = self.parse_init_out_temp(self.DEFAULT['init_out_temp'])
		self.init_temp = self.parse_init_temp(self.DEFAULT['init_temp'])


		self.server_ip = self.parser_server_ip(self.DEFAULT['server_ip'])
		self.server_port = self.parser_server_port(self.DEFAULT['server_port'])
		"""
		#try: # catch conversion exceptions
		self.target_temp = float(self.parse_value('target_temp', self.DEFAULT['target_temp']))
		self.init_temp = float(self.parse_value('init_temp', self.DEFAULT['init_temp']))
		self.init_out_temp = float(self.parse_value('init_out_temp', self.DEFAULT['init_out_temp']))
		self.temp_model = self.parse_value('temp_model', self.DEFAULT['temp_model'])
		self.presence_model = self.parse_value('presence_model', self.DEFAULT['presence_model'])
		self.valve_coef = float(self.parse_value('valve_coef', self.DEFAULT['valve_coef']))
		self.out_temp_coef = float(self.parse_value('out_temp_coef', self.DEFAULT['out_temp_coef']))
		self.server_ip = self.parse_value('server_ip', self.DEFAULT['server_ip'])
		self.server_port = int(self.parse_value('server_port', self.DEFAULT['server_port']))
		self.period = int(self.parse_value('period', self.DEFAULT['period']))
		#except:
		#	print("Nop")

	def load_cfg(self, cfg_path):
		"""
			Return an Element object, corresponding to the cml root element of the cfg file.
		"""
		# XML parsing
		tree = ET.parse(cfg_path)
		return tree.getroot()

	def parse_value(self, value_name, default=None):
		"""
			Parse the cfg file, try to find an element named after 'value_name' and return is content as string.
		"""
		return self.cfg_root.find(value_name).text

	def parse_init_out_temp(self, default=None):
		"""
			Parse the cfg file and return the initial outside temperature (in numerical 
			form) specified in it.
			If this information isn't found (or isn't valid), the default value is 
			returned (None if nothing is specified)
		"""

		cfg_init_out_temp = self.cfg_root.find('init_out_temp')
		if cfg_init_out_temp and cfg_init_out_temp.text.isnumeric():
			cfg_init_out_temp = float(cfg_init_out_temp.text)
		else: # period not specified or not numerical value
			cfg_init_out_temp = default

		return cfg_init_out_temp


	def parse_init_temp(self, default=None):
		"""
			Parse the cfg file and return the initial outside temperature (in numerical 
			form) specified in it.
			If this information isn't found (or isn't valid), the default value is 
			returned (None if nothing is specified)
		"""

		cfg_init_temp = self.cfg_root.find('init_temp')
		if cfg_init_temp and cfg_init_temp.text.isnumeric():
			cfg_init_temp = float(cfg_init_temp.text)
		else: # period not specified or not numerical value
			cfg_init_temp = default

		return cfg_init_temp

	def parse_server_ip(self, default=None):
		"""
			Parse the cfg file and return the ip of the server (in str 
			form) specified in it.
			If this information isn't found (or isn't valid), the default value is 
			returned (None if nothing is specified)
		"""
		cfg_server_ip = self.cfg_root.find('server_ip')
		if cfg_server_ip: # TODO: the ip may be invalid
			cfg_server_ip = cfg_server_ip.text
		else: # ip not specified
			cfg_server_ip = default

		return cfg_server_ip

	def parse_server_port(self, default=None):
		"""
			Parse the cfg file and return the port of the server (in numeric 
			form) specified in it.
			If this information isn't found (or isn't valid), the default value is 
			returned (None if nothing is specified)
		"""
		cfg_server_port = self.cfg_root.find('server_ip')
		if cfg_server_port and cfg_server_port.text.isnumeric():
			cfg_server_port = int(cfg_server_port.text) # TODO: What if float...
		else: # ip not specified
			cfg_server_port = default

		return cfg_server_port


	def parse_target_temp(self, default=None):
		"""
			Parse the cfg file and return the target_temp (in numerical 
			form) specified in it.
			If this information isn't found (or isn't valid), the default value is 
			returned (None if nothing is specified)
		"""

		cfg_target_temp = self.cfg_root.find('target_temp')
		if cfg_target_temp and cfg_target_temp.text.isnumeric():
			cfg_target_temp = int(cfg_target_temp.text)
		else: # period not specified or not numerical value
			cfg_target_temp = default

		return cfg_target_temp


	def parse_period(self, default=None): # TODO: this method is absolutly useless here...
		"""
			Parse the cfg file and return the period (in numerical 
			form) specified in it.
			If this information isn't found, the default value is 
			returned (None if nothing is specified)
		"""
		cfg_period = self.cfg_root.find('period')
		if cfg_period and cfg_period.text.isnumeric():
			cfg_period = int(cfg_period.text)
		else: # period not specified or not numerical value
			cfg_period = default

		return cfg_period

	def parse_temp_model(self, default=None):
		"""
			Parse cfg file and return an str telling which method have 
			to be used to simulate te variation of temperature.
			default value (if specified) is returned if this param 
			isn't found or is invalid
		"""
		cfg_temp_model = self.cfg_root.find('temp_model')

		if cfg_temp_model and cfg_temp_model.text in self.VALID_TEMP_MODEL:
			cfg_temp_model = cfg_temp_model.text
		else:
			cfg_temp_model = default

		return cfg_temp_model

	def parse_presence_model(self, default=None):
		"""
			Parse cfg file and return an str telling which method have 
			to be used to simulate te variation of presence.
			default value (if specified) is returned if this param 
			isn't found or is invalid
		"""
		cfg_presence_model = self.cfg_root.find('presence_model')

		if cfg_presence_model and cfg_presence_model.text in self.VALID_TEMP_MODEL:
			cfg_presence_model = cfg_presence_model.text
		else:
			cfg_presence_model = default

		return cfg_presence_model


class Config:
	"""
		"Abtract" class used for config file parsing.
		A class has to be created (and inherit from this one) 
		for each type of config file to parse.
		This class only defines generic methods such as the file loading, basic element research, ...
	"""
	def __init__(self, cfg_path):
		"""
			cfg_path is the path of the xml configuration file
		"""
		self.cfg_path = cfg_path
		self.cfg_root = self.load_cfg(self.cfg_path)


	def load_cfg(self, cfg_path):
		"""
			Return an Element object, corresponding to the cml root element of the cfg file.
		"""
		# XML parsing
		tree = ET.parse(cfg_path)
		return tree.getroot()


	def get_element(self, el_name, params={}):
		"""
			return an Element object matching the requested constraint.
			el_name is the name fo the wanted element
			params is an optionnal dictionnary that associate an xml parameter name to its value
		"""
		self.cfg_root.find(el_name)








sim = ThermoSim()
sim.connect_to_server()
sim.run()













