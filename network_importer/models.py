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
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Boolean,
    Enum,
    DateTime,
    Table,
    ForeignKeyConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from dsync import DSyncMixin

Base = declarative_base()

DEVICE_NAME_DEF = String(250)
SITE_NAME_DEF = String(120)
INTF_NAME_DEF = String(120)
IP_PREFIX_DEF = String(42)
VLAN_NAME_DEF = String(250)

class Site(Base, DSyncMixin):
    """
    """

    __tablename__ = "site"

    childs = ["devices", "prefixes"]
    attributes = []

    name = Column(SITE_NAME_DEF, primary_key=True)
    devices = relationship("Device", back_populates="site")
    vlans = relationship("Vlan", back_populates="site")
    prefixes = relationship("Prefix", back_populates="site")

    remote_id = Column(Integer, nullable=True)

    def __repr__(self):
        return str(self.name)


class Device(Base, DSyncMixin):
    """
    """

    __tablename__ = "device"

    childs = ["interfaces"]
    attributes = []

    name = Column(DEVICE_NAME_DEF, primary_key=True)
    site_name = Column(SITE_NAME_DEF, ForeignKey("site.name"), nullable=True)

    site = relationship("Site", back_populates="devices")
    interfaces = relationship("Interface", back_populates="device")

    remote_id = Column(Integer, nullable=True)

    def __repr__(self):
        return str(self.name)


# interface_vlans_allowed = Table('interface_vlans_allowed', Base.metadata,
#     Column('vlan_id', Integer, ForeignKey('vlan.vid')),
#     Column('site_name', SITE_NAME_DEF, ForeignKey('vlan.site_name')),
#     Column('interface_name', INTF_NAME_DEF, ForeignKey('interface.name')),
#     Column('device_name', DEVICE_NAME_DEF, ForeignKey('interface.device_name')),
# )

class Interface(Base, DSyncMixin):
    """
    """

    __tablename__ = "interface"

    childs = ["ips"]
    attributes = ["description", "mtu", "switchport_mode"]

    name = Column(INTF_NAME_DEF, primary_key=True)
    device_name = Column(
        DEVICE_NAME_DEF, ForeignKey("device.name"), nullable=False, primary_key=True
    )
    description = Column(String(250), nullable=True)
    mtu = Column(Integer, nullable=True)
    speed = Column(Integer, nullable=True)
    mode = Column(Enum("TRUNK", "ACCESS", "L3", "NONE"), nullable=True)
    switchport_mode = Column(String(50), nullable=True) # Need to convert to ENUM
    active = Column(Boolean, nullable=True)
    is_virtual = Column(Boolean, nullable=True)
    # is_lag_member = Column(Boolean, nullable=True)  # 
    parent = Column(INTF_NAME_DEF, nullable=True)
    # lag_members()

    access_vlan = Column(Integer, nullable=True)
    # allowed_vlans = relationship("Vlan",
    #                 secondary=interface_vlans_allowed)

    # Relationship
    device = relationship("Device", back_populates="interfaces")
    ips = relationship("IPAddress")


    remote_id = Column(Integer, nullable=True)

    def __repr__(self):
        return f"{self.device_name}::{self.name}"



class IPAddress(Base, DSyncMixin):
    """
    """

    __tablename__ = "ip_address"

    childs = []
    attributes = ["device_name", "interface_name"]

    address = Column(IP_PREFIX_DEF, primary_key=True)
    interface_name = Column(INTF_NAME_DEF, primary_key=True)
    device_name = Column(DEVICE_NAME_DEF, primary_key=True)
    interface = relationship("Interface", back_populates="ips")

    __table_args__ = (
        ForeignKeyConstraint(
            ["device_name", "interface_name"],
            ["interface.device_name", "interface.name"],
        ),
    )

    remote_id = Column(Integer, nullable=True)

    def __repr__(self):
        return str(self.address)


class Cable(Base, DSyncMixin):
    """ """

    __tablename__ = "cable"

    childs = []
    attributes = []

    device_a_name = Column(DEVICE_NAME_DEF, primary_key=True)
    interface_a_name = Column(INTF_NAME_DEF, primary_key=True)
    device_z_name = Column(DEVICE_NAME_DEF, primary_key=True)
    interface_z_name = Column(INTF_NAME_DEF, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["device_a_name", "interface_a_name", "device_z_name", "interface_z_name"],
            [
                "interface.device_name",
                "interface.name",
                "interface.device_name",
                "interface.name",
            ],
        ),
    )

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

    def unique_id(self):
        return "_".join(
            sorted(
                [
                    f"{self.device_a_name}:{self.interface_a_name}",
                    f"{self.device_z_name}:{self.interface_z_name}",
                ]
            )
        )

    def __repr__(self):
        return str(self.unique_id())


class Vlan(Base, DSyncMixin):
    """ """

    __tablename__ = "vlan"

    childs = []
    attributes = ["name"]

    vid = Column(Integer, primary_key=True)
    site_name = Column(SITE_NAME_DEF, ForeignKey("site.name"), primary_key=True)
    name = Column(VLAN_NAME_DEF, nullable=True)
    site = relationship("Site", back_populates="vlans")

    remote_id = Column(Integer, nullable=True)

    # interfaces_tagged = relationship("Interface",
    #                 secondary=interface_vlans_allowed,
    #                 back_populates="allowed_vlans")

class Prefix(Base, DSyncMixin):
    """
    """

    __tablename__ = "prefix"

    childs = []
    attributes = ["prefix_type"]

    prefix = Column(IP_PREFIX_DEF, primary_key=True)
    site_name = Column(SITE_NAME_DEF, ForeignKey("site.name"), primary_key=True)

    vlan_id = Column(Integer, ForeignKey("vlan.vid"), nullable=True)

    site = relationship("Site", back_populates="prefixes")
    prefix_type =  Column(Enum("AGGREGATE"), nullable=True)

    # vlan = relationship("Vlan", back_populates="prefixes")

    remote_id = Column(Integer, nullable=True)

    def __repr__(self):
        return f"{self.site_name} - {self.prefix} ({self.prefix_type})"