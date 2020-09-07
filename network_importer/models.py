"""
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
import copy
from collections import defaultdict
from typing import Set, Dict, List, Optional

from dsync import DSyncModel


class Site(DSyncModel):
    """
    """

    __modelname__ = "site"
    __identifier__ = ["name"]
    __shortname__ = []
    __attributes__ = []
    __children__ = {"device": "devices", "prefix": "prefixes"}

    name: str
    devices: List = list()
    prefixes: List = list()

    def __repr__(self):
        return str(self.name)


class Device(DSyncModel):
    """
    """

    __modelname__ = "device"
    __identifier__ = ["name"]
    __attributes__ = []
    __children__ = {"interface": "interfaces"}

    name: str
    site_name: str
    interfaces: List = list()

    platform: Optional[str]
    model: Optional[str]
    role: Optional[str]
    vendor: Optional[str]


class Interface(DSyncModel):
    """
    """

    __modelname__ = "interface"
    __identifier__ = ["device_name", "name"]
    __shortname__ = ["name"]
    __attributes__ = [
        "description",
        "mtu",
        "is_virtual",
        "is_lag",
        "is_lag_member",
        "parent",
        "switchport_mode",
    ]
    __children__ = {"ip_address": "ips", "vlan": "allowed_vlans"}

    name: str
    device_name: str

    description: Optional[str]
    mtu: Optional[int]
    speed: Optional[int]
    mode: Optional[str]  # TRUNK, ACCESS, L3, NONE
    switchport_mode: Optional[str] = "NONE"
    active: Optional[bool]
    is_virtual: Optional[bool]
    is_lag: Optional[bool]
    is_lag_member: Optional[bool]
    parent: Optional[str]

    lag_members: List[str] = list()
    allowed_vlans: List[str] = list()
    access_vlan: Optional[str]

    ips: List = list()


class IPAddress(DSyncModel):
    """
    """

    __modelname__ = "ip_address"
    __identifier__ = ["address"]
    __attributes__ = ["device_name", "interface_name"]

    address: str  # = Column(IP_PREFIX_DEF, primary_key=True)
    interface_name: Optional[str]
    device_name: Optional[str]


class Prefix(DSyncModel):
    """
    """

    __modelname__ = "prefix"
    __identifier__ = ["site_name", "prefix"]
    __attributes__ = ["prefix_type"]

    prefix: str
    site_name: Optional[str]

    vlan_id: Optional[int]
    prefix_type: Optional[str]

    # vlan = relationship("Vlan", back_populates="prefixes")


class Cable(DSyncModel):
    """ """

    __modelname__ = "cable"
    __identifier__ = [
        "device_a_name",
        "interface_a_name",
        "device_z_name",
        "interface_z_name",
    ]
    __attributes__ = []

    device_a_name: str
    interface_a_name: str
    device_z_name: str
    interface_z_name: str

    def __init__(self, *args, **kwargs):
        """ Ensure the """
        new_kwargs = copy.deepcopy(kwargs)
        devices = [kwargs["device_a_name"], kwargs["device_z_name"]]
        if sorted(devices) != devices:
            new_kwargs["device_a_name"] = kwargs["device_z_name"]
            new_kwargs["interface_a_name"] = kwargs["interface_z_name"]
            new_kwargs["device_z_name"] = kwargs["device_a_name"]
            new_kwargs["interface_z_name"] = kwargs["interface_a_name"]

        super().__init__(*args, **new_kwargs)

    def get_unique_id(self):
        return "__".join(
            sorted([f"{self.device_a_name}:{self.interface_a_name}", f"{self.device_z_name}:{self.interface_z_name}",])
        )


class Vlan(DSyncModel):
    """ """

    __modelname__ = "vlan"
    __identifier__ = ["site", "vid"]
    __attributes__ = ["name"]

    vid: int
    name: Optional[str]
    site_name: str


# class Optic(BaseModel):
#     """
#     Base Class for an optic
#     """

#     def __init__(
#         self,
#         name: str = None,
#         optic_type: str = None,
#         intf: str = None,
#         serial: str = None,
#     ):
#         """

#         Args:
#           name:  (Default value = None)
#           optic_type:  (Default value = None)
#           intf:  (Default value = None)
#           serial:  (Default value = None)

#         Returns:

#         """
#         self.optic_type = optic_type
#         self.intf = intf
#         self.serial = serial
#         self.name = name
