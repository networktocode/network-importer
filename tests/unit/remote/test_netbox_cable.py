# pylint: disable=C0116,C0121,R0801

from os import path

import pynetbox
import yaml

from network_importer.remote.netbox import NetboxCable

HERE = path.abspath(path.dirname(__file__))
FIXTURE_26 = "fixtures/netbox_26"
FIXTURE_27 = "fixtures/netbox_27"


def test_netbox27_vlan_no_tag():

    data = yaml.safe_load(open(f"{HERE}/{FIXTURE_26}/interface_connected_interface.json"))
    rem = pynetbox.core.response.Record(data, "http://mock", 1)

    cable = NetboxCable()
    cable.add(interface=rem)
    assert cable.unique_id == "amarillo:ge-0/0/0_austin:Gi0"
    assert cable.remote.id == 345

    cable = NetboxCable()
    cable.add(cable=rem.cable)
    cable.add_device("deva", "intfa")
    cable.add_device("devb", "intfb")
    assert cable.remote.id == 345
