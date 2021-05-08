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

import network_importer.config as config
import pynautobot
import pytest
import yaml
from diffsync.exceptions import ObjectNotFound
from network_importer.adapters.nautobot_api.models import NautobotDevice, NautobotVlan

ROOT = os.path.abspath(os.path.dirname(__file__))


def test_vlan_create_from_pynautobot(nautobot_api_base):
    config.load(config_data=dict())
    api = pynautobot.api(url="http://mock_nautobot", token="1234567890")

    data = yaml.safe_load(open(f"{ROOT}/../fixtures/vlan_101_no_tag.json"))
    pnb = pynautobot.core.response.Record(values=data, api=api, endpoint="eb697742-364d-4714-b585-a267c64d7720")

    item = NautobotVlan.create_from_pynautobot(diffsync=nautobot_api_base, obj=pnb, site_name="nyc")
    assert isinstance(item, NautobotVlan) is True
    assert item.remote_id == "eb697742-364d-4714-b585-a267c64d7720"
    assert item.vid == 101
    assert item.associated_devices == []


def test_vlan_create_from_pynautobot_with_tags(nautobot_api_base):

    api = pynautobot.api(url="http://mock_nautobot", token="1234567890")

    data = yaml.safe_load(open(f"{ROOT}/../fixtures/vlan_101_tags_01.json"))
    pnb = pynautobot.core.response.Record(values=data, api=api, endpoint=1)

    nautobot_api_base.add(
        NautobotDevice(name="devA", site_name="nyc", remote_id="eb697742-364d-4714-b585-a267c64d7720")
    )

    item = NautobotVlan.create_from_pynautobot(diffsync=nautobot_api_base, obj=pnb, site_name="nyc")
    assert isinstance(item, NautobotVlan) is True
    assert item.remote_id == "eb697742-364d-4714-b585-a267c64d7720"
    assert item.vid == 101
    assert item.associated_devices == ["devA"]

    # Try again with one additional device in the inventory
    nautobot_api_base.add(
        NautobotDevice(name="devB", site_name="nyc", remote_id="eb697742-364d-4714-b585-a267c64d7731")
    )
    item = NautobotVlan.create_from_pynautobot(diffsync=nautobot_api_base, obj=pnb, site_name="nyc")
    assert isinstance(item, NautobotVlan) is True
    assert item.remote_id == "eb697742-364d-4714-b585-a267c64d7720"
    assert item.vid == 101
    assert item.associated_devices == ["devA", "devB"]


def test_translate_attrs_for_nautobot_no_attrs(nautobot_api_base):

    vlan = NautobotVlan(vid=100, site_name="HQ", remote_id="eb697742-364d-4714-b585-a267c64d7720")
    nautobot_api_base.add(vlan)

    params = vlan.translate_attrs_for_nautobot({})

    assert "name" in params
    assert params["name"] == "vlan-100"
    assert "site" in params
    assert params["site"] == "a325e477-62fe-47f0-8b67-acf411b1868f"
    assert "tags" not in params


def test_translate_attrs_for_nautobot_with_partial_attrs(nautobot_api_base):

    vlan = NautobotVlan(vid=100, name="MYVLAN", site_name="HQ", remote_id="464a2de3-fd5e-4b65-a58d-e0a2a617c12e")
    nautobot_api_base.add(vlan)

    nautobot_api_base.add(
        NautobotDevice(
            name="dev1",
            site_name="HQ",
            remote_id="e0633a07-c3e2-41b0-a1df-4627392acf0a",
            device_tag_id="0bc28fc5-4e3d-4e84-b407-318c2151d64e",
        )
    )
    nautobot_api_base.add(
        NautobotDevice(
            name="dev2",
            site_name="HQ",
            remote_id="e0633a07-c3e2-41b0-a1df-4627392acf0b",
            device_tag_id="0bc28fc5-4e3d-4e84-b407-318c2151d65a",
        )
    )
    params = vlan.translate_attrs_for_nautobot({"associated_devices": ["dev1", "dev2"]})

    assert "name" not in params
    assert "site" in params
    assert params["site"] == "a325e477-62fe-47f0-8b67-acf411b1868f"
    assert "tags" in params
    assert sorted(params["tags"]) == ["0bc28fc5-4e3d-4e84-b407-318c2151d64e", "0bc28fc5-4e3d-4e84-b407-318c2151d65a"]


def test_translate_attrs_for_nautobot_with_attrs(nautobot_api_base):

    vlan = NautobotVlan(vid=100, site_name="HQ", remote_id="464a2de3-fd5e-4b65-a58d-e0a2a617c12e")
    nautobot_api_base.add(vlan)

    nautobot_api_base.add(
        NautobotDevice(
            name="dev1",
            site_name="HQ",
            remote_id="e0633a07-c3e2-41b0-a1df-4627392acf0a",
            device_tag_id="0bc28fc5-4e3d-4e84-b407-318c2151d64e",
        )
    )
    nautobot_api_base.add(
        NautobotDevice(
            name="dev2",
            site_name="HQ",
            remote_id="e0633a07-c3e2-41b0-a1df-4627392acf0b",
            device_tag_id="0bc28fc5-4e3d-4e84-b407-318c2151d65a",
        )
    )
    params = vlan.translate_attrs_for_nautobot({"name": "VOICE", "associated_devices": ["dev1", "dev2"]})

    assert "name" in params
    assert params["name"] == "VOICE"
    assert "site" in params
    assert params["site"] == "a325e477-62fe-47f0-8b67-acf411b1868f"
    assert "tags" in params
    assert sorted(params["tags"]) == ["0bc28fc5-4e3d-4e84-b407-318c2151d64e", "0bc28fc5-4e3d-4e84-b407-318c2151d65a"]


def test_translate_attrs_for_nautobot_with_missing_devices(nautobot_api_base):

    vlan = NautobotVlan(vid=100, site_name="HQ", remote_id="464a2de3-fd5e-4b65-a58d-e0a2a617c12e")
    nautobot_api_base.add(vlan)

    nautobot_api_base.add(
        NautobotDevice(
            name="dev1",
            site_name="HQ",
            remote_id="e0633a07-c3e2-41b0-a1df-4627392acf0a",
            device_tag_id="0bc28fc5-4e3d-4e84-b407-318c2151d64e",
        )
    )
    params = vlan.translate_attrs_for_nautobot({"name": "VOICE", "associated_devices": ["dev1", "dev2"]})

    assert "name" in params
    assert params["name"] == "VOICE"
    assert "site" in params
    assert params["site"] == "a325e477-62fe-47f0-8b67-acf411b1868f"
    assert "tags" in params
    assert sorted(params["tags"]) == ["0bc28fc5-4e3d-4e84-b407-318c2151d64e"]


def test_translate_attrs_for_nautobot_missing_site(nautobot_api_base):

    vlan = NautobotVlan(vid=100, site_name="NOTPRESENT", remote_id="464a2de3-fd5e-4b65-a58d-e0a2a617c12e")
    nautobot_api_base.add(vlan)

    with pytest.raises(ObjectNotFound):
        vlan.translate_attrs_for_nautobot({})
        assert True


def test_update_clean_tags_no_incoming_tags(nautobot_api_base):

    vlan = NautobotVlan(vid=100, site_name="HQ", remote_id="464a2de3-fd5e-4b65-a58d-e0a2a617c12e")
    nautobot_api_base.add(vlan)

    api = pynautobot.api(url="http://mock_nautobot", token="1234567890")
    data = yaml.safe_load(open(f"{ROOT}/../fixtures/vlan_101_tags_01.json"))
    pnb = pynautobot.core.response.Record(values=data, api=api, endpoint="eb697742-364d-4714-b585-a267c64d7720")

    params = vlan.translate_attrs_for_nautobot({"name": "VOICE"})

    clean_params = vlan.update_clean_tags(nb_params=params, obj=pnb)

    assert "tags" not in clean_params


def test_update_clean_tags_with_incoming_tags(nautobot_api_base):

    vlan = NautobotVlan(vid=100, site_name="HQ", remote_id="464a2de3-fd5e-4b65-a58d-e0a2a617c12e")
    nautobot_api_base.add(vlan)

    nautobot_api_base.add(
        NautobotDevice(
            name="dev1",
            site_name="HQ",
            remote_id="e0633a07-c3e2-41b0-a1df-4627392acf0a",
            device_tag_id="0bc28fc5-4e3d-4e84-b407-318c2151d64e",
        )
    )
    nautobot_api_base.add(
        NautobotDevice(
            name="dev2",
            site_name="HQ",
            remote_id="e0633a07-c3e2-41b0-a1df-4627392acf0b",
            device_tag_id="0bc28fc5-4e3d-4e84-b407-318c2151d65a",
        )
    )

    api = pynautobot.api(url="http://mock_nautobot", token="1234567890")
    data = yaml.safe_load(open(f"{ROOT}/../fixtures/vlan_101_tags_01.json"))
    pnb = pynautobot.core.response.Record(values=data, api=api, endpoint="eb697742-364d-4714-b585-a267c64d7720")

    params = vlan.translate_attrs_for_nautobot({"name": "VOICE", "associated_devices": ["dev1", "dev2"]})
    clean_params = vlan.update_clean_tags(nb_params=params, obj=pnb)

    assert "tags" in clean_params
    print(clean_params)
    assert sorted(clean_params["tags"]) == [
        "0bc28fc5-4e3d-4e84-b407-318c2151d64e",
        "0bc28fc5-4e3d-4e84-b407-318c2151d65a",
        "999121c7-37d6-44a8-83f9-61706e915bde",
        "d0c52a6c-b3e9-4234-98ef-ee9b76ca31db",
        "fd6809fa-26cf-47b2-8742-974cd4d22ca9",
    ]
