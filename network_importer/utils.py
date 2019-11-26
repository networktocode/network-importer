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

import time


find_digit = re.compile("\D?(\d+)\D?")
def sort_by_digits(if_name):
    return tuple(map(int, find_digit.findall(if_name)))


def jinja_filter_toyaml_list(value):
    return yaml.dump(value, default_flow_style=None)


def jinja_filter_toyaml_dict(value):
    return yaml.dump(value, default_flow_style=False)


class TimeTracker(object):

    def __init__(self):

        self.start_time = time.time()
        self.times = []
        self.nbr_devices = None
        self.add_checkpoint("start")

    def add_checkpoint(self, name):
        self.times.append(dict(name=name, time=time.time()))
        return True

    def sef_nbr_devices(self, nbr):
        self.nbr_devices = nbr

    def print_all(self):
        
        for i in range(0, len(self.times)):

            checkpnt = self.times[i]
            
            if i == 0:
               continue
            
            checkpnt = self.times[i]
            previous = self.times[i-1]

            device_info = ""
            if self.nbr_devices:
                device_info = f" || From previous/dev {(checkpnt['time']-previous['time'])/self.nbr_devices}s"

            print(f"{checkpnt['name']}: From Previous {checkpnt['time']-previous['time']}s || From start {checkpnt['time']-self.start_time}s{device_info}")