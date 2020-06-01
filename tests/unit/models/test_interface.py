# pylint: disable=C0116,C0121,R0801

"""
(c) 2019 Network To Code

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
import pandas as pd
import network_importer.config as config
from network_importer.model import (
    NetworkImporterDevice,
    NetworkImporterInterface,
    NetworkImporterIP,
)

from network_importer.base_model import Interface


def test_add_batfish_interface_loopback():
    """
    Verify `add_batfish_interface()`  is working properly for a Loopback interface
    """
    config.load_config()

    data = {
        "Interface": "Loopback1",
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

    intf = NetworkImporterInterface(name=data["Interface"], device_name="dev")
    intf.add_batfish_interface(pd.Series(data))

    assert isinstance(intf.local, Interface)
    assert intf.local.is_virtual
    assert not intf.local.is_lag
    assert not intf.local.is_lag_member


def test_add_batfish_interface_phy_intf_ether_std():
    """
    Verify `add_batfish_interface()` is working properly for a standalone physical interface
    """
    config.load_config()

    data = {
        "Interface": "GigabitEthernet0/0/0",
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

    intf = NetworkImporterInterface(name=data["Interface"], device_name="dev")
    intf.add_batfish_interface(pd.Series(data))

    assert isinstance(intf.local, Interface)
    assert not intf.local.is_virtual
    assert not intf.local.is_lag
    assert not intf.local.is_lag_member


def test_add_batfish_interface_intf_ether_sub():
    """
    Verify `add_batfish_interface()` is working properly for a sub interface of a physical interface
    """
    config.load_config()

    data = {
        "Interface": "GigabitEthernet0/0/0.201",
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

    intf = NetworkImporterInterface(name=data["Interface"], device_name="dev")
    intf.add_batfish_interface(pd.Series(data))

    assert isinstance(intf.local, Interface)
    assert intf.local.is_virtual
    assert not intf.local.is_lag
    assert not intf.local.is_lag_member


def test_add_batfish_interface_intf_lag_member():
    """
    Verify `add_batfish_interface()` is working properly for lag member
    """
    config.load_config()

    data = {
        "Interface": "TenGigabitEthernet2/1/3",
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

    intf = NetworkImporterInterface(name=data["Interface"], device_name="dev")
    intf.add_batfish_interface(pd.Series(data))

    assert isinstance(intf.local, Interface)
    assert not intf.local.is_virtual
    assert not intf.local.is_lag
    assert intf.local.is_lag_member
    assert intf.local.allowed_vlans == [10, 11, 12, 40]


def test_add_batfish_interface_intf_lag():
    """
    Verify `add_batfish_interface()` is working properly for lag
    """
    config.load_config()

    data = {
        "Interface": "Port-Channel11",
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

    intf = NetworkImporterInterface(name=data["Interface"], device_name="dev")
    intf.add_batfish_interface(pd.Series(data))

    assert isinstance(intf.local, Interface)
    assert not intf.local.is_virtual
    assert intf.local.is_lag
    assert not intf.local.is_lag_member
    assert intf.local.allowed_vlans == [10, 11, 12, 40]


def test_add_batfish_interface_intf_serial():
    """
    Verify `add_batfish_interface()` is working properly for serial interface
    """
    config.load_config()

    data = {
        "Interface": "Serial0/1/0:15",
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

    intf = NetworkImporterInterface(name=data["Interface"], device_name="dev")
    intf.add_batfish_interface(pd.Series(data))

    assert isinstance(intf.local, Interface)
    assert not intf.local.is_virtual
    assert not intf.local.is_lag
    assert not intf.local.is_lag_member


def test_ip_on_interface():
    """
    Verify `ip_on_interface()` function of `NetworkImporterInterface` class returns expected value
    """

    test_device = NetworkImporterDevice(name="test_device")
    test_device.interfaces["GigabitEthernet0/0"] = NetworkImporterInterface(
        name="GigabitEthernet0/0", device_name=test_device.name,
    )
    test_device.add_ip(
        intf_name="GigabitEthernet0/0", ip=NetworkImporterIP(address="10.0.0.1/30"),
    )
    assert test_device.interfaces["GigabitEthernet0/0"].ip_on_interface("10.0.0.1/30")
    assert not test_device.interfaces["GigabitEthernet0/0"].ip_on_interface(
        "10.1.1.3/24"
    )
