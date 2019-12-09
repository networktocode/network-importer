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

# ---------------------------------------------------
# Base Classes, might need to find a better naming
# ---------------------------------------------------


class BaseModel(object):

    exclude_from_diff = []

    def get_attrs_diff(self):
        attrs = list(vars(self).keys())
        for attr in self.exclude_from_diff:
            if attr in attrs:
                attrs.remove(attr)

        return attrs


class Vlan(BaseModel):

    exclude_from_diff = ["related_devices"]

    def __init__(self, name=None, vid=None, site=None):
        self.name = name

        if vid:
            self.vid = int(vid)
        else:
            self.vid = None

        self.site = site
        self.related_devices = [] 


class Interface(BaseModel):

    exclude_from_diff = ["lag_members", "speed"]

    def __init__(self, name=None):
        self.name = name
        self.device_name = None
        self.mode = None  # TRUNK, ACCESS, L3, NONE
        self.is_virtual = None
        self.active = None
        self.is_lag_member = None
        self.parent = None
        self.is_lag = None
        self.lag_members = None

        self.description = None
        self.speed = None
        self.mtu = None
        self.switchport_mode = None  # = None
        self.access_vlan = None
        self.allowed_vlans = None

class IPAddress(BaseModel):

    exclude_from_diff = ["family"]

    def __init__(self, address=None):
        self.address = address
        self.family = None

class Optic(BaseModel):

    def __init__(self, name=None, optic_type=None, intf=None, serial=None):
        self.optic_type = optic_type
        self.intf = intf
        self.serial = serial
        self.name = name
