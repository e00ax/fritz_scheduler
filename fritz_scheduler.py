import appdaemon.plugins.hass.hassapi as hass
import adbase as ad
import configparser
from datetime import date
import datetime

#
# Fritz scheduler
#
class FritzScheduler(ad.ADBase):
    
    def initialize(self):
        self.adapi = self.get_ad_api()

        # DHT22
        self.dht22 = self.adapi.get_entity(self.args["dht22"], namespace="hass")
        self.dht22_state = self.dht22.get_state(attribute="state")

        # Fritz DECT 301
        self.fritz = self.adapi.get_entity(self.args["fritz"], namespace="hass")
        self.fritz_state = self.fritz.get_state(attribute="current_temperature")

        # Read ini file
        config = configparser.ConfigParser()
        config.read('/config/appdaemon/apps/' + self.args["ini"])

        # Format time object
        self.today = date.today()
        day = self.today.strftime("%a")
        self.time = datetime.datetime.now().strftime("%H:%M:%S")
        self.timestamp = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")

        # Split time for current date
        daily_schedule = config['auto'][day]
        self.daily_schedule_list = daily_schedule.split('#')

        # Run callback
        #self.adapi.run_in(self.fritz_cb, 20)
        self.adapi.run_minutely(self.fritz_cb, datetime.datetime.now())

    #
    # Fritz callback
    #
    def fritz_cb(self, kwargs):
        # Loop over schedule
        for i in self.daily_schedule_list:
            daily_schedule_time = i.split('-')
            start = daily_schedule_time[0]
            end = daily_schedule_time[1]
            target = daily_schedule_time[2]

            if (self.is_hour_between(start, end)):
                # Calc new temperature
                self.calc_temp(self.dht22_state, self.fritz_state, target)

                # Set new temperature
                self.set_temp()

                self.adapi.log('####################################################')
                self.adapi.log('Timestamp: ' + str(self.timestamp))
                self.adapi.log('Start: ' + start)
                self.adapi.log('End: ' + end)
                self.adapi.log('Target: ' + target)
                self.adapi.log('New Temperature: ' + str(self.new_temp))
                self.adapi.log('####################################################')

    #
    # Calculate new temperature
    #
    def calc_temp(self, dht22_temp, fritz_temp, target):
        diff = float(dht22_temp) - float(target)

        # DHT22 temp higher than target => cool down
        if (diff > 0):
            self.new_temp = target

        # DHT22 temp lower than target => heat
        else:
           self.new_temp = round(float(fritz_temp) - diff, 1)

    #
    # Set fritz target temp to new temp
    #
    def set_temp(self):
        self.adapi.call_service(
            "climate/set_temperature", 
            entity_id=self.args["fritz"], 
            temperature=self.new_temp,
            namespace="hass"
        )

    #
    # Check for current time
    #  
    def is_hour_between(self, start, end):
        # Time Now
        now = datetime.datetime.now().time()

        # Format the datetime string
        time_format = '%H:%M'

        # Convert the start and end datetime to just time
        start = datetime.datetime.strptime(start, time_format).time()
        end = datetime.datetime.strptime(end, time_format).time()

        # Conditions
        is_between = False
        is_between |= start <= now <= end
        is_between |= end <= start and (start <= now or now <= end)

        return is_between
