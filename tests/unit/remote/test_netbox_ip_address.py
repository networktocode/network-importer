from os import path

import yaml
import pynetbox

from network_importer.remote.netbox import NetboxIPAddress

HERE = path.abspath(path.dirname(__file__))
FIXTURE_27 = "fixtures/netbox_27"


def test_netbox27_vlan_no_tag():

    data = yaml.safe_load(open(f"{HERE}/{FIXTURE_27}/ip_address.json"))
    rem = pynetbox.models.ipam.IpAddresses(data, "http://mock", 1)

    ip = NetboxIPAddress()
    ip.add(rem)

    assert ip.address == "10.63.0.2/31"
    assert str(ip.family) == "IPv4"
