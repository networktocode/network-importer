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
from typing import List, Optional

from dsync import DSyncModel


class Site(DSyncModel):
    """
    """

    __modelname__ = "site"
    __identifier__ = ["name"]
    __shortname__ = []
    __attributes__ = []
    __children__ = {"vlan": "vlans", "prefix": "prefixes"}

    name: str

    prefixes: List = list()
    vlans: List[str] = list()

    # def __repr__(self):
    #     return str(self.name)


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
        # "mtu",
        "is_virtual",
        "is_lag",
        "is_lag_member",
        "parent",
        "mode",
        "switchport_mode",
        "allowed_vlans",
        "access_vlan",
    ]
    __children__ = {"ip_address": "ips"}

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

    ips: List[str] = list()


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

    vlan: Optional[str]
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

    source: Optional[str]
    is_valid: bool = True
    error: Optional[str]

    def __init__(self, *args, **kwargs):
        """ Ensure the """

        if "device_a_name" not in kwargs or "device_z_name" not in kwargs:
            raise ValueError("device_a_name and device_z_name are mandatory")
        if not kwargs["device_a_name"] or not kwargs["device_z_name"]:
            raise ValueError("device_a_name and device_z_name are mandatory and must not be None")

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

    def get_device_intf(self, side):

        if side.lower() == "a":
            return self.device_a_name, self.interface_a_name
        elif side.lower() == "z":
            return self.device_z_name, self.interface_z_name
        else:
            raise ValueError("side must be either 'a' or 'z'")


class Vlan(DSyncModel):
    """ """

    __modelname__ = "vlan"
    __identifier__ = ["site_name", "vid"]
    __attributes__ = ["name", "associated_devices"]

    vid: int
    site_name: str
    name: Optional[str]

    associated_devices: List[str] = list()


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
