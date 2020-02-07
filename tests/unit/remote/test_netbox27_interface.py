# pylint: disable=C0116,C0121,R0801

from os import path

import pynetbox
import yaml

import network_importer.config as config
from network_importer.remote.netbox import Netbox27Interface

HERE = path.abspath(path.dirname(__file__))
FIXTURES = "fixtures/netbox_27"

# ---------------------------------------------------------------------
# ADD
# ---------------------------------------------------------------------


def test_netbox27_add_interface_access():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_access.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox27Interface()
    intf.add(rem)

    assert intf.is_lag == False
    assert intf.is_virtual == False
    assert intf.is_lag_member == None
    assert intf.switchport_mode == "ACCESS"
    assert intf.access_vlan == 300


def test_netbox27_add_interface_lag_member():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_lag_member.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox27Interface()
    intf.add(rem)

    assert intf.is_lag == False
    assert intf.is_virtual == False
    assert intf.is_lag_member == True
    assert intf.switchport_mode == "NONE"
    assert intf.access_vlan == None
    assert intf.allowed_vlans == None


def test_netbox27_add_interface_lag_trunk():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_lag_trunk.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox27Interface()
    intf.add(rem)

    assert intf.is_lag == True
    assert intf.is_virtual == False
    assert intf.is_lag_member == None
    assert intf.switchport_mode == "TRUNK"
    assert intf.access_vlan == 300
    assert intf.allowed_vlans == [300, 301]


def test_netbox27_add_interface_loopback():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_loopback.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox27Interface()
    intf.add(rem)

    assert intf.is_lag == False
    assert intf.is_virtual == True
    assert intf.is_lag_member == None
    assert intf.switchport_mode == "NONE"
    assert intf.access_vlan == None
    assert intf.allowed_vlans == None


# ---------------------------------------------------------------------
# Get Properties
# ---------------------------------------------------------------------


def test_netbox26_properties_interface_loopback():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/interface_loopback.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = Netbox27Interface()
    intf.add(rem)

    intf_prop = Netbox27Interface.get_properties(intf)

    assert intf_prop["type"] == "virtual"
    assert intf_prop["mode"] == None
    assert intf_prop["enabled"] == True
