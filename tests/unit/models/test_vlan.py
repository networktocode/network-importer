# pylint: disable=C0116,C0121,R0801

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
from network_importer.models import Vlan


def test_add_device():
    """Validate that add device is workign properly and that the same device won't be added twice."""
    vlan = Vlan(vid=120, site_name="nyc")
    assert len(vlan.associated_devices) == 0
    vlan.add_device("device1")
    assert len(vlan.associated_devices) == 1
    vlan.add_device("device2")
    assert len(vlan.associated_devices) == 2
    vlan.add_device("device1")
    assert len(vlan.associated_devices) == 2
