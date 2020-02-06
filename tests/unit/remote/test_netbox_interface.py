from os import path

import yaml
import pynetbox

import network_importer.config as config
from network_importer.remote.netbox import NetboxInterface_26, NetboxInterface_27

HERE = path.abspath(path.dirname(__file__))
FIXTURE_27 = "fixtures/netbox_27"


def test_netbox27_interface():

    config.load_config()
    data = yaml.safe_load(open(f"{HERE}/{FIXTURE_27}/interface_physical.json"))
    rem = pynetbox.models.dcim.Interfaces(data, "http://mock", 1)

    intf = NetboxInterface_27()
    intf.add(rem)

    assert ip.name == "TenGigabitEthernet1/0/4"
