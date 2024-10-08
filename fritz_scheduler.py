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

        # Run callback
        #self.adapi.run_in(self.fritz_cb, 20)
        self.adapi.run_minutely(self.fritz_cb, datetime.datetime.now())

    #
    # Fritz callback
    #
    def fritz_cb(self, kwargs):
        """
        Loop over all DHT22 sensors

        Attach them with FRITZ DECT 30X and schedule.ini

        Important:
        Association is 1:1 (dht22/fritz/ini)
        """
        for i in range(len(self.args["dht22"])):
            # Counter for use as indices
            self.counter = i

            # DHT22
            self.dht22 = self.adapi.get_entity(self.args["dht22"][i], namespace="hass")
            self.dht22_state = self.dht22.get_state(attribute="state")

            # Fritz DECT 301
            self.fritz = self.adapi.get_entity(self.args["fritz"][i], namespace="hass")
            self.fritz_state = self.fritz.get_state(attribute="current_temperature")

            # Read ini file
            #config = configparser.ConfigParser()
            #config.read('schedule.ini')

            schedule = {
                "Mon":"00:00-07:00-10#07:01-16:00-19#16:01-23:59-19",
                "Tue":"00:00-07:00-10#07:01-16:00-19#16:01-23:59-19",
                "Wed":"00:00-07:00-10#07:01-16:00-19#16:01-23:59-19",
                "Thu":"00:00-07:00-10#07:01-16:00-19#16:01-23:59-19",
                "Fri":"00:00-07:00-10#07:01-16:00-19#16:01-23:59-19",
                "Sat":"00:00-09:00-10#08:01-23:59-19",
                "Sun":"00:00-09:00-10#09:01-23:59-19"
            }

            # Format time object
            self.today = date.today()
            day = self.today.strftime("%a")
            self.time = datetime.datetime.now().strftime("%H:%M:%S")
            self.timestamp = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")

            # Split time for current date
            daily_schedule = schedule[day]
            self.daily_schedule_list = daily_schedule.split('#')

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

                    # Log to appdaemon.log
                    self.adapi.log('####################################################')
                    self.adapi.log('DHT22 sensor: ' + self.args["dht22"][self.counter])
                    self.adapi.log('Fritz sensor: ' + self.args["fritz"][self.counter])
                    self.adapi.log('Timestamp: ' + str(self.timestamp))
                    self.adapi.log('Start: ' + start)
                    self.adapi.log('End: ' + end)
                    self.adapi.log('Target: ' + target)
                    self.adapi.log('Diff: ' + str(self.diff))
                    self.adapi.log('DHT22 State: ' + str(self.dht22_state))
                    self.adapi.log('Fritz State: ' + str(self.fritz_state))
                    self.adapi.log('New Temperature: ' + str(self.new_temp))
                    self.adapi.log('####################################################')

    #
    # Calculate new temperature
    #
    def calc_temp(self, dht22_temp, fritz_temp, target):
        self.diff = float(dht22_temp) - float(target)

        # DHT22 temp higher than target => cool down
        if (self.diff >= 0):
            self.new_temp = target

        # DHT22 temp lower than target => heat
        else:
           self.new_temp = round(float(fritz_temp) - self.diff, 1)

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
