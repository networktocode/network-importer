# pylint: disable=C0116,C0121,R0801

from os import path

import pynetbox
import yaml

from network_importer.remote.netbox import NetboxIPAddress

HERE = path.abspath(path.dirname(__file__))
FIXTURE_27 = "fixtures/netbox_27"


def test_netbox27_vlan_no_tag():

    data = yaml.safe_load(open(f"{HERE}/{FIXTURE_27}/ip_address.json"))
    rem = pynetbox.models.ipam.IpAddresses(data, "http://mock", 1)

    ipaddr = NetboxIPAddress()
    ipaddr.add(rem)

    assert ipaddr.address == "10.63.0.2/31"
    assert str(ipaddr.family) == "IPv4"
