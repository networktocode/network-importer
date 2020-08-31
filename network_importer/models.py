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
from pydantic import BaseModel

from dsync import DSyncMixin


class Site(BaseModel, DSyncMixin):
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


class Device(BaseModel, DSyncMixin):
    """
    """

    __modelname__ = "device"
    __identifier__ = ["name"]
    __attributes__ = []
    __children__ = {"interface": "interfaces"}

    name: str
    site_name: str
    interfaces: List = list()


# interface_vlans_allowed = Table('interface_vlans_allowed', Base.metadata,
#     Column('vlan_id', Integer, ForeignKey('vlan.vid')),
#     Column('site_name', SITE_NAME_DEF, ForeignKey('vlan.site_name')),
#     Column('interface_name', INTF_NAME_DEF, ForeignKey('interface.name')),
#     Column('device_name', DEVICE_NAME_DEF, ForeignKey('interface.device_name')),
# )


class Interface(BaseModel, DSyncMixin):
    """
    """

    __tablename__ = "interface"

    __modelname__ = "interface"
    __identifier__ = ["device_name", "name"]
    __shortname__ = ["name"]
    __attributes__ = ["description", "mtu", "switchport_mode"]
    __children__ = {"ip_address": "ips"}

    name: str
    device_name: str

    description: Optional[str]
    mtu: Optional[int]
    speed: Optional[int]
    mode: Optional[str]
    switchport_mode: Optional[str]
    active: Optional[bool]
    is_virtual: Optional[bool]
    is_lag: Optional[bool]
    is_lag_member: Optional[bool]

    lag_members: Optional[List[str]]
    parent: Optional[str]

    # access_vlan = Column(Integer, nullable=True)
    # allowed_vlans = relationship("Vlan",
    #                 secondary=interface_vlans_allowed)

    ips: List = list()


class IPAddress(BaseModel, DSyncMixin):
    """
    """

    __modelname__ = "ip_address"
    __identifier__ = ["address"]
    __attributes__ = ["device_name", "interface_name"]

    address: str  # = Column(IP_PREFIX_DEF, primary_key=True)
    interface_name: Optional[str]
    device_name: Optional[str]


class Prefix(BaseModel, DSyncMixin):
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


class Cable(BaseModel, DSyncMixin):
    """ """

    __modelname__ = "cable"
    __identifier__ = [
        "device_a_name",
        "interface_a_name",
        "device_z_name",
        "interface_z_name",
    ]
    __attributes__ = []
    __children_types__ = []

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
            sorted(
                [
                    f"{self.device_a_name}:{self.interface_a_name}",
                    f"{self.device_z_name}:{self.interface_z_name}",
                ]
            )
        )


# class Vlan(BaseModel, DSyncMixin):
#     """ """

#     __tablename__ = "vlan"


#     __modelname__ = "vlan"
#     __identifier__ = ["site", "vid"]
#     __attributes__ = ["name"]
#     __children_types__ = []


#     vid: int
#     site: Site
#     name: str

#     # remote_id = Column(Integer, nullable=True)

#     # interfaces_tagged = relationship("Interface",
#     #                 secondary=interface_vlans_allowed,
#     #                 back_populates="allowed_vlans")
