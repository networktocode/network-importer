import copy
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Table,
    ForeignKeyConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class BaseNetMod:
    def __iter__(self):
        for v in self.values:
            yield v, getattr(self, v)

    def get_type(self):
        return self.__tablename__

    def get_keys(self):
        return {pk.name: getattr(self, pk.name) for pk in self.__table__.primary_key}

    def get_attrs(self):
        return {attr: getattr(self, attr) for attr in self.attributes}


class Site(Base, BaseNetMod):
    """
    """

    __tablename__ = "site"

    childs = ["devices"]
    attributes = []

    name = Column(String(250), primary_key=True)
    devices = relationship("Device", back_populates="site")
    vlans = relationship("Vlan", back_populates="site")
    prefixes = relationship("Prefix", back_populates="site")

    def __repr__(self):
        return str(self.name)


class Device(Base, BaseNetMod):
    """
    """

    __tablename__ = "device"

    childs = ["interfaces"]
    attributes = []

    name = Column(String(250), primary_key=True)
    site_name = Column(String(250), ForeignKey("site.name"), nullable=True)
    site = relationship("Site", back_populates="devices")
    interfaces = relationship("Interface", back_populates="device")

    def __repr__(self):
        return str(self.name)


class Interface(Base, BaseNetMod):
    """
    """

    __tablename__ = "interface"

    childs = ["ips"]
    attributes = ["description", "mtu", "switchport_mode"]

    name = Column(String(250), primary_key=True)
    description = Column(String(250), nullable=True)
    mtu = Column(Integer, nullable=True)
    switchport_mode = Column(String(250), nullable=True)

    device_name = Column(
        Integer, ForeignKey("device.name"), nullable=False, primary_key=True
    )
    device = relationship("Device", back_populates="interfaces")
    ips = relationship("IPAddress")

    def __repr__(self):
        return f"{self.device_name}::{self.name}"


class IPAddress(Base, BaseNetMod):
    """
    """

    __tablename__ = "ip_address"

    childs = []
    attributes = ["device_name", "interface_name"]

    address = Column(String(250), primary_key=True)
    interface_name = Column(String(250))
    device_name = Column(String(250))

    __table_args__ = (
        ForeignKeyConstraint(
            ["device_name", "interface_name"],
            ["interface.device_name", "interface.name"],
        ),
    )

    def __repr__(self):
        return str(self.address)


class Cable(Base, BaseNetMod):
    """ """

    __tablename__ = "cable"

    childs = []
    attributes = []

    device_a_name = Column(String(250), primary_key=True)
    interface_a_name = Column(String(250), primary_key=True)
    device_z_name = Column(String(250), primary_key=True)
    interface_z_name = Column(String(250), primary_key=True)

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


class Vlan(Base, BaseNetMod):
    """ """

    __tablename__ = "vlan"

    childs = []
    attributes = ["name"]

    name = Column(String(250), nullable=True)
    vid = Column(Integer, primary_key=True)
    site_name = Column(String(250), ForeignKey("site.name"), primary_key=True)
    site = relationship("Site", back_populates="vlans")

class Prefix(Base, BaseNetMod):
    """
    """

    __tablename__ = "prefix"

    childs = []
    attributes = []

    prefix = Column(String(250),primary_key=True)
    site_name = Column(String(250), ForeignKey("site.name"), nullable=True)
    site = relationship("Site", back_populates="prefixes")
