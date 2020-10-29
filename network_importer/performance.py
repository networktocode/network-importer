"""TimeTracker class to track the performance of the application.

(c) 2020 Network To Code

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

import os
import logging
import math
from time import strftime, time
import network_importer.config as config

TIME_TRACKER = None
LOGGER = logging.getLogger("network-importer")  # pylint: disable=C0103

# pylint: disable=global-statement


def init():
    """Initialize the global time tracker."""
    global TIME_TRACKER

    if not TIME_TRACKER:
        TIME_TRACKER = TimeTracker()


def print_from_ms(msec) -> str:
    """Result time in human readable format from milliseconds.

    Args:
      ms: time in millisecond

    Returns:
        str: Time in human readable format
    """
    ms_per_sec = 1000
    ms_per_min = ms_per_sec * 60

    minutes = math.floor((msec / ms_per_min))
    seconds = math.floor(((msec - (ms_per_min * minutes)) / ms_per_sec))
    millis = msec - (ms_per_min * minutes) - (ms_per_sec * seconds)

    if minutes == 0 and seconds == 0:
        return "%dms" % (millis)
    if minutes == 0:
        return "%ds %dms" % (seconds, millis)

    return "%dm %ds %dms" % (minutes, seconds, millis)


def timeit(method):
    """Decorator to record the execution time of a function."""
    global TIME_TRACKER

    def timed(*args, **kw):
        """Decorator to record the execution time of a function and store the result in TIME_TRACKER."""
        timestart = time()
        result = method(*args, **kw)
        timeend = time()

        name = method.__name__.upper()
        exec_time = int((timeend - timestart) * 1000)

        if TIME_TRACKER:
            TIME_TRACKER.times[name] = exec_time

        return result

    return timed


class TimeTracker:
    """TimeTracker object used to keep track of different information around the execution of network importer."""

    def __init__(self):
        """Initialize the TimeTracker object."""
        self.start_time = time()
        self.times = {}
        self.nbr_devices = None

    def set_nbr_devices(self, nbr: int):
        """Define the number of devices."""
        self.nbr_devices = nbr

    def print_all(self):
        """Print all information related to time tracking to file if enabled in the configuration."""
        if not os.path.exists(config.SETTINGS.logs.performance_log_directory):
            os.makedirs(config.SETTINGS.logs.performance_log_directory)
            LOGGER.debug("Directory %s was missing, created it", config.SETTINGS.logs.performance_log_directory)

        perflog_filename = strftime("%Y-%m-%d_%H-%M-%S.log")
        perflog_file_path = config.SETTINGS.logs.performance_log_directory + "/" + perflog_filename

        with open(perflog_file_path, "w") as file_:

            if self.nbr_devices:
                file_.write(f"Report for {self.nbr_devices} devices\n")

            total_time = exec_time = int((time() - self.start_time) * 1000)
            file_.write(f"Total execution time: {print_from_ms(total_time)}\n")

            for funct, exec_time in self.times.items():
                if self.nbr_devices:
                    exec_time_per_dev = exec_time / self.nbr_devices
                    log = f"{funct} finished in {print_from_ms(exec_time)} | {print_from_ms(exec_time_per_dev)} per device"

                else:
                    log = f"{funct} finished in {print_from_ms(exec_time)}"

                file_.write(log + "\n")
