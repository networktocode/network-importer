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

from network_importer.adapters.netbox_api.models import NetboxDevice

ROOT = os.path.abspath(os.path.dirname(__file__))


def test_get_device_tag_id(netbox_api_base):

    device = NetboxDevice(name="dev1", site_name="HQ", remote_id=32, device_tag_id=12)
    netbox_api_base.add(device)
    assert device.get_device_tag_id() == 12


def test_get_device_tag_id_get_tag(requests_mock, netbox_api_base):

    data = yaml.safe_load(open(f"{ROOT}/../fixtures/netbox_29/tag_01_list.json"))
    requests_mock.get("http://mock/api/extras/tags/?name=device%3Ddev1", json=data, status_code=200)

    device = NetboxDevice(name="dev1", site_name="HQ", remote_id=32)
    netbox_api_base.add(device)

    assert device.get_device_tag_id() == 8


def test_get_device_tag_id_create_tag(requests_mock, netbox_api_base, empty_netbox_query):

    data = yaml.safe_load(open(f"{ROOT}/../fixtures/netbox_29/tag_01.json"))
    requests_mock.get("http://mock/api/extras/tags/?name=device%3Ddev1", json=empty_netbox_query, status_code=200)
    requests_mock.post("http://mock/api/extras/tags/", json=data, status_code=201)

    device = NetboxDevice(name="dev1", site_name="HQ", remote_id=32)
    netbox_api_base.add(device)

    assert device.get_device_tag_id() == 88
