from netmod.models import *
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NetboxSite(Site):

    remote_id = Column(Integer, nullable=True)


class NetboxDevice(Device):

    remote_id = Column(Integer, nullable=True)


class NetboxInterface(Interface):

    remote_id = Column(Integer, nullable=True)


class NetboxIPAddress(IPAddress):

    remote_id = Column(Integer, nullable=True)


class NetboxCable(Cable):

    remote_id = Column(Integer, nullable=True)
    termination_a_id = Column(Integer, nullable=True)
    termination_z_id = Column(Integer, nullable=True)
