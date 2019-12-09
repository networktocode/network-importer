"""
(c) 2019 Network To Code

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import math
import os
from time import strftime, time
import network_importer.config as config
import logging

time_tracker = None
logger = logging.getLogger("network-importer")


def init():
    global time_tracker

    if not time_tracker:
        time_tracker = TimeTracker()


def print_from_ms(ms):

    ms_per_sec = 1000
    ms_per_min = ms_per_sec * 60

    minutes = math.floor((ms / ms_per_min))
    seconds = math.floor(((ms - (ms_per_min * minutes)) / ms_per_sec))
    millis = ms - (ms_per_min * minutes) - (ms_per_sec * seconds)

    if minutes == 0 and seconds == 0:
        return "%dms" % (millis)
    elif minutes == 0:
        return "%ds %dms" % (seconds, millis)
    else:
        return "%dm %ds %dms" % (minutes, seconds, millis)


def timeit(method):
    global time_tracker

    def timed(*args, **kw):
        ts = time()
        result = method(*args, **kw)
        te = time()

        name = method.__name__.upper()
        exec_time = int((te - ts) * 1000)

        if time_tracker:
            time_tracker.times[name] = exec_time

        return result

    return timed


class TimeTracker(object):
    def __init__(self):
        self.start_time = time()
        self.times = {}
        self.nbr_devices = None

    def set_nbr_devices(self, nbr):
        self.nbr_devices = nbr

    def print_all(self):

        if not os.path.exists(config.logs["performance_log_directory"]):
            os.makedirs(config.logs["performance_log_directory"])
            logger.debug(
                f"Directory {config.logs['performance_log_directory']} was missing, created it"
            )

        perflog_filename = strftime("%Y-%m-%d_%H-%M-%S.log")
        perflog_file_path = (
            config.logs["performance_log_directory"] + "/" + perflog_filename
        )

        with open(perflog_file_path, "w") as f:

            if self.nbr_devices:
                f.write(f"Report for {self.nbr_devices} devices\n")
            
            f.write(f"Total execution time: {print_from_ms(time()-self.start_time)}\n")

            for funct, exec_time in self.times.items():
                if self.nbr_devices:
                    exec_time_per_dev = exec_time / self.nbr_devices
                    log = f"{funct} finished in {print_from_ms(exec_time)} | {print_from_ms(exec_time_per_dev)} per device"

                else:
                    log = f"{funct} finished in {print_from_ms(exec_time)}"

                f.write(log + "\n")
