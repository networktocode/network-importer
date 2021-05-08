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

from network_importer.adapters.nautobot_api.models import NautobotDevice

ROOT = os.path.abspath(os.path.dirname(__file__))


def test_nautobot_get_device_tag_id():

    device = NautobotDevice(
        name="dev12", site_name="HQ", remote_id=32, device_tag_id="eb697742-364d-4714-b585-a267c64d7720"
    )
    assert device.get_device_tag_id() == "eb697742-364d-4714-b585-a267c64d7720"


def test_nautobot_get_device_tag_id_get_tag(requests_mock, nautobot_api_base):

    data = yaml.safe_load(open(f"{ROOT}/../fixtures/tag_01_list.json"))
    requests_mock.get("http://mock_nautobot/api/extras/tags/?name=device%3Ddev1", json=data, status_code=200)

    device = NautobotDevice(name="dev1", site_name="HQ", remote_id=32)
    nautobot_api_base.add(device)

    assert device.get_device_tag_id() == "eb697742-364d-4714-b585-a267c64d7720"


def test_get_device_tag_id_create_tag(requests_mock, nautobot_api_base, empty_nautobot_query):

    data = yaml.safe_load(open(f"{ROOT}/../fixtures/tag_01.json"))
    requests_mock.get(
        "http://mock_nautobot/api/extras/tags/?name=device%3Ddev1", json=empty_nautobot_query, status_code=200
    )
    requests_mock.post("http://mock_nautobot/api/extras/tags/", json=data, status_code=201)

    device = NautobotDevice(name="dev1", site_name="HQ", remote_id=32)
    nautobot_api_base.add(device)

    assert device.get_device_tag_id() == "3fed3ac5-c623-493c-b029-87487830d159"
