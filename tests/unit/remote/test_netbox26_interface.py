# pylint: disable=C0116,C0121,R0801

from os import path

import pynetbox
import yaml

import network_importer.config as config
from network_importer.remote.netbox import Netbox26Interface

HERE = path.abspath(path.dirname(__file__))
FIXTURES = "fixtures/netbox_26"


def test_netbox26_interface_access():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_access.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox26Interface()
    intf.add(rem)

    assert intf.is_lag == False
    assert intf.is_virtual == False
    assert intf.is_lag_member == None
    assert intf.switchport_mode == "ACCESS"
    assert intf.access_vlan == 1


def test_netbox26_interface_trunk():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_trunk.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox26Interface()
    intf.add(rem)

    assert intf.is_lag == False
    assert intf.is_virtual == False
    assert intf.is_lag_member == None
    assert intf.switchport_mode == "TRUNK"
    assert intf.access_vlan == 5
    assert sorted(intf.allowed_vlans) == [5, 14, 18]


def test_netbox26_interface_lag_member():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_lag_member.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox26Interface()
    intf.add(rem)

    assert intf.is_lag == False
    assert intf.is_virtual == False
    assert intf.is_lag_member == True
    assert intf.switchport_mode == "NONE"
    assert intf.access_vlan == None
    assert intf.allowed_vlans == None


def test_netbox26_interface_lag():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_lag.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox26Interface()
    intf.add(rem)

    assert intf.is_lag == True
    assert intf.is_virtual == False
    assert intf.is_lag_member == None
    assert intf.switchport_mode == "NONE"
    assert intf.access_vlan == None
    assert intf.allowed_vlans == None


def test_netbox26_interface_loopback():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_loopback.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox26Interface()
    intf.add(rem)

    assert intf.is_lag == False
    assert intf.is_virtual == True
    assert intf.is_lag_member == None
    assert intf.switchport_mode == "NONE"
    assert intf.access_vlan == None
    assert intf.allowed_vlans == None
