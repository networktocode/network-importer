# pylint: disable=C0116,C0121,R0801

from os import path

import pynetbox
import yaml

from network_importer.remote.netbox import NetboxVlan

HERE = path.abspath(path.dirname(__file__))
FIXTURE_27 = "fixtures/netbox_27"


def test_netbox27_vlan_no_tag():

    data = yaml.safe_load(open(f"{HERE}/{FIXTURE_27}/vlan_101_no_tag.json"))
    rem = pynetbox.core.response.Record(data, "http://mock", 1)

    vlan = NetboxVlan()
    vlan.add(rem)

    assert vlan.vid == 101
    assert vlan.name == "R101"
    assert vlan.related_devices == []


def test_netbox27_vlan_tag():

    data = yaml.safe_load(open(f"{HERE}/{FIXTURE_27}/vlan_101_tags_01.json"))
    rem = pynetbox.core.response.Record(data, "http://mock", 1)

    vlan = NetboxVlan()
    vlan.add(rem)

    assert vlan.vid == 101
    assert vlan.name == "R101"
    assert sorted(vlan.related_devices) == ["devA", "devB"]
