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
import pytest

import pynetbox

from diffsync.exceptions import ObjectNotFound
from network_importer.adapters.netbox_api.models import NetboxVlan, NetboxDevice

ROOT = os.path.abspath(os.path.dirname(__file__))
FIXTURE_28 = "../fixtures/netbox_28"
FIXTURE_29 = "../fixtures/netbox_29"


def test_vlan_create_from_pynetbox(netbox_api_base):

    api = pynetbox.api(url="http://mock", token="1234567890")

    data = yaml.safe_load(open(f"{ROOT}/{FIXTURE_29}/vlan_101_no_tag.json"))
    pnb = pynetbox.core.response.Record(values=data, api=api, endpoint=1)

    item = NetboxVlan.create_from_pynetbox(diffsync=netbox_api_base, obj=pnb, site_name="nyc")
    assert isinstance(item, NetboxVlan) is True
    assert item.remote_id == 1
    assert item.vid == 101
    assert item.associated_devices == []


def test_vlan_create_from_pynetbox_with_tags(netbox_api_base):

    api = pynetbox.api(url="http://mock", token="1234567890")

    data = yaml.safe_load(open(f"{ROOT}/{FIXTURE_29}/vlan_101_tags_01.json"))
    pnb = pynetbox.core.response.Record(values=data, api=api, endpoint=1)

    netbox_api_base.add(NetboxDevice(name="devA", site_name="nyc", remote_id=30))

    item = NetboxVlan.create_from_pynetbox(diffsync=netbox_api_base, obj=pnb, site_name="nyc")
    assert isinstance(item, NetboxVlan) is True
    assert item.remote_id == 1
    assert item.vid == 101
    assert item.associated_devices == ["devA"]

    # Try again with one additional device in the inventory
    netbox_api_base.add(NetboxDevice(name="devB", site_name="nyc", remote_id=31))
    item = NetboxVlan.create_from_pynetbox(diffsync=netbox_api_base, obj=pnb, site_name="nyc")
    assert isinstance(item, NetboxVlan) is True
    assert item.remote_id == 1
    assert item.vid == 101
    assert item.associated_devices == ["devA", "devB"]


def test_translate_attrs_for_netbox_no_attrs(netbox_api_base):

    vlan = NetboxVlan(vid=100, site_name="HQ", remote_id=30)
    netbox_api_base.add(vlan)

    params = vlan.translate_attrs_for_netbox({})

    assert "name" in params
    assert params["name"] == "vlan-100"
    assert "site" in params
    assert params["site"] == 10
    assert "tags" not in params


def test_translate_attrs_for_netbox_with_partial_attrs(netbox_api_base):

    vlan = NetboxVlan(vid=100, name="MYVLAN", site_name="HQ", remote_id=30)
    netbox_api_base.add(vlan)

    netbox_api_base.add(NetboxDevice(name="dev1", site_name="HQ", remote_id=32, device_tag_id=12))
    netbox_api_base.add(NetboxDevice(name="dev2", site_name="HQ", remote_id=33, device_tag_id=13))
    params = vlan.translate_attrs_for_netbox({"associated_devices": ["dev1", "dev2"]})

    assert "name" not in params
    assert "site" in params
    assert params["site"] == 10
    assert "tags" in params
    assert sorted(params["tags"]) == [12, 13]


def test_translate_attrs_for_netbox_with_attrs(netbox_api_base):

    vlan = NetboxVlan(vid=100, site_name="HQ", remote_id=30)
    netbox_api_base.add(vlan)

    netbox_api_base.add(NetboxDevice(name="dev1", site_name="HQ", remote_id=32, device_tag_id=12))
    netbox_api_base.add(NetboxDevice(name="dev2", site_name="HQ", remote_id=33, device_tag_id=13))
    params = vlan.translate_attrs_for_netbox({"name": "VOICE", "associated_devices": ["dev1", "dev2"]})

    assert "name" in params
    assert params["name"] == "VOICE"
    assert "site" in params
    assert params["site"] == 10
    assert "tags" in params
    assert sorted(params["tags"]) == [12, 13]


def test_translate_attrs_for_netbox_with_missing_devices(netbox_api_base):

    vlan = NetboxVlan(vid=100, site_name="HQ", remote_id=30)
    netbox_api_base.add(vlan)

    netbox_api_base.add(NetboxDevice(name="dev1", site_name="HQ", remote_id=32, device_tag_id=12))
    params = vlan.translate_attrs_for_netbox({"name": "VOICE", "associated_devices": ["dev1", "dev2"]})

    assert "name" in params
    assert params["name"] == "VOICE"
    assert "site" in params
    assert params["site"] == 10
    assert "tags" in params
    assert sorted(params["tags"]) == [12]


def test_translate_attrs_for_netbox_missing_site(netbox_api_base):

    vlan = NetboxVlan(vid=100, site_name="NOTPRESENT", remote_id=30)
    netbox_api_base.add(vlan)

    with pytest.raises(ObjectNotFound):
        vlan.translate_attrs_for_netbox({})
        assert True


def test_update_clean_tags_no_incoming_tags(netbox_api_base):

    vlan = NetboxVlan(vid=100, site_name="HQ", remote_id=30)
    netbox_api_base.add(vlan)

    api = pynetbox.api(url="http://mock", token="1234567890")
    data = yaml.safe_load(open(f"{ROOT}/{FIXTURE_29}/vlan_101_tags_01.json"))
    pnb = pynetbox.core.response.Record(values=data, api=api, endpoint=1)

    params = vlan.translate_attrs_for_netbox({"name": "VOICE"})

    clean_params = vlan.update_clean_tags(nb_params=params, obj=pnb)

    assert "tags" not in clean_params


def test_update_clean_tags_with_incoming_tags(netbox_api_base):

    vlan = NetboxVlan(vid=100, site_name="HQ", remote_id=30)
    netbox_api_base.add(vlan)

    netbox_api_base.add(NetboxDevice(name="dev1", site_name="HQ", remote_id=32, device_tag_id=12))
    netbox_api_base.add(NetboxDevice(name="dev2", site_name="HQ", remote_id=33, device_tag_id=13))

    api = pynetbox.api(url="http://mock", token="1234567890")
    data = yaml.safe_load(open(f"{ROOT}/{FIXTURE_29}/vlan_101_tags_01.json"))
    pnb = pynetbox.core.response.Record(values=data, api=api, endpoint=1)

    params = vlan.translate_attrs_for_netbox({"name": "VOICE", "associated_devices": ["dev1", "dev2"]})
    clean_params = vlan.update_clean_tags(nb_params=params, obj=pnb)

    assert "tags" in clean_params
    assert sorted(clean_params["tags"]) == [1, 2, 3, 12, 13]
