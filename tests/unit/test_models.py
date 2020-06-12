import pytest

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import FlushError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from network_importer.models import *

engine = create_engine("sqlite:///:memory:") # echo=True)
Session = sessionmaker(bind=engine)

@pytest.fixture()
def session():
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_device(session):
    """ """
    dev = Device(name="device1")
    session.add(dev)
    devs = session.query(Device).all()
    assert len(devs) == 1

def test_interface(session):

    dev = Device(name="device1")
    intf1 = Interface(name="intf1", device_name="device1")
    session.add(dev)
    session.add(intf1)
    session.commit()
    assert intf1.device == dev
    assert dev.interfaces == [intf1]

    # Ensure the primary Key is working properly
    with pytest.raises(FlushError):
        intf2 = Interface(name="intf1", device_name="device1")
        session.add(intf2)
        session.commit()

def test_interface_mode(session):

    dev = Device(name="device1")
    intf1 = Interface(name="intf1", device_name="device1", mode="TRUNK")
    session.add(dev)
    session.add(intf1)
    session.commit()
    assert intf1.mode == "TRUNK"

    # Ensure the Enum is working properly
    with pytest.raises(IntegrityError):
        intf1.mode = "NOTSUPPORTED"
        session.commit()

def test_ip_address(session):

    dev = Device(name="device1")
    intf1 = Interface(name="intf1", device_name="device1")
    ip1 = IPAddress(address="10.10.10.1/32", interface=intf1)
    session.add(dev)
    session.add(intf1)
    session.add(ip1)
    session.commit()
    assert ip1.interface == intf1
    assert intf1.ips == [ip1]

    ip2 = IPAddress(address="10.10.10.2/32", interface_name="intf1", device_name="device1")
    session.add(ip2)
    session.commit()
    assert ip2.interface == intf1
    assert len(intf1.ips) == 2
