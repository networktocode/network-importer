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

from network_importer.models import Interface, Vlan


def test_check_data_consistency(network_importer_base):
    adapter = network_importer_base
    vlan110 = Vlan(vid="110", site_name="sfo")
    vlan120 = Vlan(vid="120", site_name="sfo")
    intf1 = Interface(
        name="et-0/0/0",
        device_name="spine1",
        allowed_vlans=[vlan110.get_unique_id(), vlan120.get_unique_id(), "vlan_ddd"],
    )

    adapter.add(vlan110)
    adapter.add(vlan120)
    adapter.add(intf1)

    adapter.check_data_consistency()

    assert len(intf1.allowed_vlans) == 2
    assert intf1.allowed_vlans[0] == vlan110.get_unique_id()
    assert vlan110.associated_devices[0] == "spine1"
    assert vlan120.associated_devices[0] == "spine1"
