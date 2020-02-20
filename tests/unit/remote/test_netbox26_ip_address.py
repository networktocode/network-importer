# pylint: disable=C0116,C0121,R0801

from os import path

import pynetbox
import yaml

from network_importer.remote.netbox import NetboxIPAddress

HERE = path.abspath(path.dirname(__file__))
FIXTURES = "fixtures/netbox_26"


def test_netbox26_vlan_no_tag():

    data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/ip_address.json"))
    rem = pynetbox.models.ipam.IpAddresses(data, "http://mock", 1)

    ipaddr = NetboxIPAddress()
    ipaddr.add(rem)

    assert ipaddr.address == "10.10.10.2/23"
    assert str(ipaddr.family) == "IPv4"
