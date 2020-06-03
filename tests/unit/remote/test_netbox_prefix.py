# pylint: disable=C0116,C0121,R0801

from os import path

import pynetbox
import yaml

from network_importer.remote.netbox import NetboxPrefix

HERE = path.abspath(path.dirname(__file__))
FIXTURE_27 = "fixtures/netbox_27"


def test_netbox27_prefix_no_vlan():

    data = yaml.safe_load(open(f"{HERE}/{FIXTURE_27}/prefix_no_vlan.json"))
    rem = pynetbox.core.response.Record(data, "http://mock", 1)

    item = NetboxPrefix()
    item.add(rem)

    assert item.prefix == "10.1.111.0/24"
    assert item.vlan == None


def test_netbox27_prefix_vlan():

    data = yaml.safe_load(open(f"{HERE}/{FIXTURE_27}/prefix_vlan.json"))
    rem = pynetbox.core.response.Record(data, "http://mock", 1)

    item = NetboxPrefix()
    item.add(rem)

    assert item.prefix == "10.1.111.0/24"
    assert item.vlan == 111
