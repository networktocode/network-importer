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

from network_importer.model import (
    NetworkImporterDevice,
    NetworkImporterInterface,
    NetworkImporterIP,
)


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
