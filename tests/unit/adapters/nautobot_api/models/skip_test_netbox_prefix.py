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

from network_importer.adapters.nautobot_api.models import NautobotPrefix

ROOT = os.path.abspath(os.path.dirname(__file__))


@pytest.mark.skip()
def test_translate_attrs_for_nautobot_default(nautobot_api_base):

    prefix = NautobotPrefix(diffsync=nautobot_api_base, prefix="10.1.111.0/24", site_name="HQ", remote_id=44)

    expected_nb_params = {"prefix": "10.1.111.0/24", "status": "active", "site": 10}
    nb_params = prefix.translate_attrs_for_nautobot(attrs={})

    assert nb_params == expected_nb_params


@pytest.mark.skip()
def test_translate_attrs_for_nautobot_with_vlan(nautobot_api_base):

    prefix = NautobotPrefix(diffsync=nautobot_api_base, prefix="10.1.111.0/24", site_name="HQ", remote_id=44)

    expected_nb_params = {"prefix": "10.1.111.0/24", "status": "active", "site": 10, "vlan": 23}
    nb_params = prefix.translate_attrs_for_nautobot(attrs=dict(vlan="HQ__111"))

    assert nb_params == expected_nb_params


@pytest.mark.skip()
def test_translate_attrs_for_nautobot_with_absent_vlan(nautobot_api_base):

    prefix = NautobotPrefix(diffsync=nautobot_api_base, prefix="10.1.111.0/24", site_name="HQ", remote_id=44)

    expected_nb_params = {"prefix": "10.1.111.0/24", "status": "active", "site": 10}
    nb_params = prefix.translate_attrs_for_nautobot(attrs=dict(vlan="HQ__112"))

    assert nb_params == expected_nb_params


@pytest.mark.skip()
def test_create_prefix(requests_mock, nautobot_api_base):

    data = yaml.safe_load(open(f"{ROOT}/../fixtures/nautobot_28/prefix_no_vlan.json"))

    requests_mock.post("http://mock/api/ipam/prefixes/", json=data, status_code=201)
    ip_address = NautobotPrefix.create(
        diffsync=nautobot_api_base, ids=dict(prefix="10.1.111.0/24", site_name="HQ"), attrs={}
    )

    assert isinstance(ip_address, NautobotPrefix) is True
    assert ip_address.remote_id == 44
    assert ip_address.vlan is None


@pytest.mark.skip()
def test_update_prefix(requests_mock, nautobot_api_base):

    data_no_vlan = yaml.safe_load(open(f"{ROOT}/../fixtures/nautobot_28/prefix_no_vlan.json"))
    data_vlan = yaml.safe_load(open(f"{ROOT}/../fixtures/nautobot_28/prefix_vlan.json"))

    remote_id = data_no_vlan["id"]

    requests_mock.get(f"http://mock/api/ipam/prefixes/{remote_id}/", json=data_no_vlan, status_code=200)
    requests_mock.patch(f"http://mock/api/ipam/prefixes/{remote_id}/", json=data_vlan, status_code=200)
    prefix = NautobotPrefix(diffsync=nautobot_api_base, prefix="10.1.111.0/24", site_name="HQ", remote_id=remote_id)

    prefix.update(attrs=dict(vlan="HQ__111"))
    assert prefix.vlan == "HQ__111"


@pytest.mark.skip()
def test_create_prefix_with_vlan(requests_mock, nautobot_api_base):

    data = yaml.safe_load(open(f"{ROOT}/../fixtures/nautobot_28/prefix_vlan.json"))

    requests_mock.post("http://mock/api/ipam/prefixes/", json=data, status_code=201)
    prefix = NautobotPrefix.create(
        diffsync=nautobot_api_base, ids=dict(prefix="10.1.111.0/24", site_name="HQ"), attrs=dict(vlan="HQ__111")
    )

    assert isinstance(prefix, NautobotPrefix) is True
    assert prefix.remote_id == 44
    assert prefix.vlan == "HQ__111"


@pytest.mark.skip()
def test_translate_attrs_for_nautobot_w_vlan(nautobot_api_base):

    prefix = NautobotPrefix(diffsync=nautobot_api_base, prefix="10.1.111.0/24", site_name="HQ", remote_id=30)
    nautobot_api_base.add(prefix)

    params = prefix.translate_attrs_for_nautobot({"vlan": "HQ__111"})

    assert "prefix" in params
    assert params["site"] == 10
    assert params["vlan"] == 23


@pytest.mark.skip()
def test_translate_attrs_for_nautobot_wo_vlan(nautobot_api_base):

    prefix = NautobotPrefix(diffsync=nautobot_api_base, prefix="10.1.111.0/24", site_name="HQ", remote_id=30)
    nautobot_api_base.add(prefix)

    params = prefix.translate_attrs_for_nautobot({"vlan": None})

    assert "prefix" in params
    assert params["site"] == 10
    assert "vlan" not in params
