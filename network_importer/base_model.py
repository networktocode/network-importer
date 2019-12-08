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

    name = None
    vid = None
    site = None

    def __init__(self, name=None, vid=None, site=None):
        self.name = name
        self.vid = int(vid)
        self.site = site


class Interface(BaseModel):

    name = None
    device_name = None
    mode = None  # TRUNK, ACCESS, L3, NONE
    is_virtual = None
    active = None
    is_lag_member = None
    parent = None
    is_lag = None
    lag_members = None

    description = None
    speed = None
    mtu = None
    switchport_mode = None  # = None
    access_vlan = None
    allowed_vlans = None

    exclude_from_diff = ["lag_members"]

    def __init__(self, name=None):
        self.name = name


class IPAddress(BaseModel):
    family = None
    address = None

    def __init__(self, address=None):
        self.address = address


class Optic(BaseModel):
    optic_type = None
    intf = None
    serial = None
    name = None

    def __init__(self, name=None, optic_type=None, intf=None, serial=None):
        self.optic_type = optic_type
        self.intf = intf
        self.serial = serial
        self.name = name