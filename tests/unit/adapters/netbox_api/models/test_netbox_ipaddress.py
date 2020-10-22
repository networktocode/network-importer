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
import os
import yaml

from network_importer.adapters.netbox_api.models import NetboxIPAddress

ROOT = os.path.abspath(os.path.dirname(__file__))


def test_create_ip_address_interface(requests_mock, netbox_api_base):

    with open(f"{ROOT}/../fixtures/netbox_28/ip_address.json") as file:
        data = yaml.safe_load(file)

    requests_mock.post("http://mock/api/ipam/ip-addresses/", json=data, status_code=201)
    ip_address = NetboxIPAddress.create(
        dsync=netbox_api_base,
        ids=dict(address="10.63.0.2/31"),
        attrs=dict(interface_name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02"),
    )

    assert isinstance(ip_address, NetboxIPAddress) is True
    assert ip_address.remote_id == 15


def test_create_ip_address_no_interface(requests_mock, netbox_api_base):

    with open(f"{ROOT}/../fixtures/netbox_28/ip_address.json") as file:
        data = yaml.safe_load(file)

    requests_mock.post("http://mock/api/ipam/ip-addresses/", json=data, status_code=201)
    ip_address = NetboxIPAddress.create(dsync=netbox_api_base, ids=dict(address="10.63.0.2/31"), attrs=dict())

    assert isinstance(ip_address, NetboxIPAddress) is True
    assert ip_address.remote_id == 15
