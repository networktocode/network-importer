"""
(c) 2020 Network To Code

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from pybatfish.datamodel.primitives import Interface as BFInterface

import network_importer.config as config
from network_importer.models import Interface

ETHERNET_1 = {
    "Interface": BFInterface(hostname="spine1", interface="GigabitEthernet0/0/0"),
    "Active": True,
    "Speed": 1000000000,
    "MTU": 1500,
    "Switchport_Mode": "NONE",
    "Switchport": False,
    "Native_VLAN": None,
    "Encapsulation_VLAN": None,
    "Description": "my description",
    "Channel_Group_Members": [],
    "Channel_Group": None,
}

LOOPBACK_1 = {
    "Interface": BFInterface(hostname="spine1", interface="Loopback1"),
    "Active": True,
    "Speed": None,
    "MTU": 1500,
    "Switchport_Mode": "NONE",
    "Switchport": False,
    "Native_VLAN": None,
    "Encapsulation_VLAN": None,
    "Description": "intf1 description",
    "Channel_Group_Members": [],
    "Channel_Group": None,
}


L3_SUB_INTF_1 = {
    "Interface": BFInterface(hostname="spine1", interface="GigabitEthernet0/0/0.201"),
    "Active": True,
    "Speed": 1000000000,
    "MTU": 1500,
    "Switchport_Mode": "NONE",
    "Switchport": False,
    "Native_VLAN": None,
    "Encapsulation_VLAN": 201,
    "Description": "my description",
    "Channel_Group_Members": [],
    "Channel_Group": None,
}

LAG_MEMBER_1 = {
    "Interface": BFInterface(hostname="spine1", interface="TenGigabitEthernet2/1/3"),
    "Active": True,
    "Speed": 10000000000,
    "MTU": 1500,
    "Allowed_VLANs": "10-12,40",
    "Switchport_Mode": "TRUNK",
    "Switchport": True,
    "Native_VLAN": 1,
    "Encapsulation_VLAN": None,
    "Description": "my description",
    "Channel_Group_Members": [],
    "Channel_Group": "Port-Channel111",
}

LAG_1 = {
    "Interface": BFInterface(hostname="spine1", interface="Port-Channel11"),
    "Active": True,
    "Speed": None,
    "MTU": 1500,
    "Allowed_VLANs": "10-12,40",
    "Switchport_Mode": "TRUNK",
    "Switchport": True,
    "Native_VLAN": 1,
    "Encapsulation_VLAN": None,
    "Description": "my description",
    "Channel_Group_Members": ["TenGigabitEthernet2/1/3", "TenGigabitEthernet2/1/4"],
    "Channel_Group": None,
}

SERIAL_1 = {
    "Interface": BFInterface(hostname="spine1", interface="Serial0/1/0:15"),
    "Active": True,
    "Speed": None,
    "MTU": 1500,
    "Allowed_VLANs": "",
    "Switchport_Mode": "NONE",
    "Switchport": False,
    "Native_VLAN": None,
    "Encapsulation_VLAN": None,
    "Description": "my description",
    "Channel_Group_Members": [],
    "Channel_Group": None,
}


def test_load_batfish_interface_loopback(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load()

    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=LOOPBACK_1)

    assert isinstance(intf, Interface)
    assert intf.is_virtual
    assert not intf.is_lag
    assert not intf.is_lag_member


def test_load_batfish_interface_phy_intf_ether_std(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load()

    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=ETHERNET_1)

    assert isinstance(intf, Interface)
    assert not intf.is_virtual
    assert not intf.is_lag
    assert not intf.is_lag_member


def test_load_batfish_interface_intf_ether_sub(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load()

    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=L3_SUB_INTF_1)

    assert isinstance(intf, Interface)
    assert intf.is_virtual
    assert not intf.is_lag
    assert not intf.is_lag_member
    assert intf.allowed_vlans == ["sfo__201"]

    assert "sfo__201" in adapter._data['vlan']

def test_load_batfish_interface_intf_lag_member(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load()

    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=LAG_MEMBER_1)

    assert isinstance(intf, Interface)
    assert not intf.is_virtual
    assert not intf.is_lag
    assert intf.is_lag_member
    assert intf.allowed_vlans == ["sfo__10", "sfo__11", "sfo__12", "sfo__40"]


def test_load_batfish_interface_intf_lag(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load()

    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=LAG_1)

    assert isinstance(intf, Interface)
    assert not intf.is_virtual
    assert intf.is_lag
    assert not intf.is_lag_member
    assert intf.allowed_vlans == ["sfo__10", "sfo__11", "sfo__12", "sfo__40"]


def test_add_batfish_interface_intf_serial(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load()

    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=SERIAL_1)

    assert isinstance(intf, Interface)
    assert not intf.is_virtual
    assert not intf.is_lag
    assert not intf.is_lag_member


# -------------------------------------------


def test_load_batfish_interface_description(network_importer_base, site_sfo, dev_spine1):
    """Check if the description is properly processed and stripped of whitespaces."""
    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load()

    data = LOOPBACK_1
    data["description"] = "  intf1 description  "

    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=data)

    assert isinstance(intf, Interface)
    assert intf.is_virtual
    assert intf.description == "intf1 description"


def test_load_batfish_intf_no_import_vlans_sub_intf(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load(config_data=dict(main=dict(import_vlans=False)))
    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=L3_SUB_INTF_1)

    assert isinstance(intf, Interface)
    assert intf.access_vlan is None
    assert intf.allowed_vlans == []


def test_load_batfish_intf_no_import_vlans_lag(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load(config_data=dict(main=dict(import_vlans=False)))
    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=LAG_1)

    assert isinstance(intf, Interface)
    assert intf.access_vlan is None
    assert intf.allowed_vlans == []


def test_load_batfish_intf_no_import_vlans_lag_members(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)

    config.load(config_data=dict(main=dict(import_vlans=False)))
    intf = adapter.load_batfish_interface(site=site_sfo, device=dev_spine1, intf=LAG_MEMBER_1)

    assert isinstance(intf, Interface)
    assert intf.access_vlan is None
    assert intf.allowed_vlans == []
