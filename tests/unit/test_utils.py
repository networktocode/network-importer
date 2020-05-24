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

from network_importer.utils import (
    expand_vlans_list,
    sort_by_digits,
    is_interface_physical,
    is_interface_lag,
)


def test_expand_vlans_list():
    """
    Test expand VLANs
    """

    assert expand_vlans_list("10-11") == [10, 11]
    assert expand_vlans_list("20-24") == [20, 21, 22, 23, 24]


def test_sort_by_digits():
    """
    Test sort by digits
    """

    assert sort_by_digits("Eth0/2/3") == (0, 2, 3,)
    assert sort_by_digits("Eth0/2/543/14/6") == (0, 2, 543, 14, 6,)
    assert sort_by_digits("Eth0") == (0,)
    assert sort_by_digits("Eth") == ()


def test_is_interface_physical():
    """
    Test is_interface_physical
    """
    assert is_interface_physical("GigabitEthernet0/0/2") == True
    assert is_interface_physical("GigabitEthernet0/0/2.890") == False
    assert is_interface_physical("GigabitEthernet0/0/2.1") == False
    assert is_interface_physical("Ethernet0.1") == False
    assert is_interface_physical("Ethernet1") == True
    assert is_interface_physical("Serial0/1/0:15") == True
    assert is_interface_physical("Service-Engine0/1/0") == True
    assert is_interface_physical("Service-Engine0/1/0.152") == False
    assert is_interface_physical("GigabitEthernet0") == True
    assert is_interface_physical("ge-0/0/0") == True
    assert is_interface_physical("ge-0/0/0.10") == False
    assert is_interface_physical("lo0.0") == False
    assert is_interface_physical("Loopback1") == False
    assert is_interface_physical("Vlan108") == False
    assert is_interface_physical("ae0.100") == False


def test_is_interface_lag():
    """
    Test is_interface_log
    """
    assert is_interface_lag("port-channel100") == True
    assert is_interface_lag("Port-Channel100") == True
    assert is_interface_lag("ae0") == True
    assert is_interface_lag("ae0.100") == None
    assert is_interface_lag("Port-Channel100") == True
    assert is_interface_lag("GigabitEthernet0/0/2") == None
    assert is_interface_lag("GigabitEthernet0/0/2.890") == None
    assert is_interface_lag("GigabitEthernet0/0/2.1") == None
    assert is_interface_lag("Ethernet0.1") == None
    assert is_interface_lag("Ethernet1") == None
    assert is_interface_lag("Serial0/1/0:15") == None
    assert is_interface_lag("Service-Engine0/1/0") == None
    assert is_interface_lag("Service-Engine0/1/0.152") == None
    assert is_interface_lag("GigabitEthernet0") == None
    assert is_interface_lag("ge-0/0/0") == None
    assert is_interface_lag("ge-0/0/0.10") == None
    assert is_interface_lag("lo0.0") == None
    assert is_interface_lag("Loopback1") == None
    assert is_interface_lag("Vlan108") == None
