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

from network_importer.models import IPAddress, Prefix


def test_add_prefix_from_ip_base(network_importer_base, site_sfo):
    adapter = network_importer_base
    adapter.add(site_sfo)

    prefix = adapter.add_prefix_from_ip(
        ip_address=IPAddress(address="10.10.10.1/24", device_name="device1", interface_name="Intf1"), site=site_sfo
    )

    assert isinstance(prefix, Prefix)
    assert adapter.get(Prefix, identifier=prefix.get_unique_id())


def test_add_prefix_from_ip_mask_32(network_importer_base, site_sfo):
    adapter = network_importer_base
    adapter.add(site_sfo)

    prefix = adapter.add_prefix_from_ip(
        ip_address=IPAddress(address="10.10.10.1/32", device_name="device1", interface_name="Intf1"), site=site_sfo
    )

    assert prefix is False


def test_add_prefix_from_ip_mask_31(network_importer_base, site_sfo):
    adapter = network_importer_base
    adapter.add(site_sfo)

    prefix = adapter.add_prefix_from_ip(
        ip_address=IPAddress(address="10.10.10.1/31", device_name="device1", interface_name="Intf1"), site=site_sfo
    )

    assert isinstance(prefix, Prefix)
    assert adapter.get(Prefix, identifier=prefix.get_unique_id())
