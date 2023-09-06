"""test for NautobotPrefix model."""
import os
import yaml

from network_importer.adapters.nautobot_api.models import NautobotPrefix

ROOT = os.path.abspath(os.path.dirname(__file__))


def test_translate_attrs_for_nautobot_default(nautobot_api_base):
    prefix = NautobotPrefix(
        diffsync=nautobot_api_base,
        prefix="10.1.111.0/24",
        site_name="HQ",
        remote_id="014b6519-bf43-40f7-a40f-d5abb9828cd2",
    )

    expected_nb_params = {"prefix": "10.1.111.0/24", "status": "active", "site": "a325e477-62fe-47f0-8b67-acf411b1868f"}
    nb_params = prefix.translate_attrs_for_nautobot(attrs={})

    assert nb_params == expected_nb_params


def test_translate_attrs_for_nautobot_with_vlan(nautobot_api_base):
    prefix = NautobotPrefix(
        diffsync=nautobot_api_base,
        prefix="10.1.111.0/24",
        site_name="HQ",
        remote_id="014b6519-bf43-40f7-a40f-d5abb9828cd2",
    )

    expected_nb_params = {
        "prefix": "10.1.111.0/24",
        "status": "active",
        "site": "a325e477-62fe-47f0-8b67-acf411b1868f",
        "vlan": "464a2de3-fd5e-4b65-a58d-e0a2a617c12e",
    }
    nb_params = prefix.translate_attrs_for_nautobot(attrs=dict(vlan="HQ__111"))

    assert nb_params == expected_nb_params


def test_translate_attrs_for_nautobot_with_absent_vlan(nautobot_api_base):
    prefix = NautobotPrefix(
        diffsync=nautobot_api_base,
        prefix="10.1.111.0/24",
        site_name="HQ",
        remote_id="014b6519-bf43-40f7-a40f-d5abb9828cd2",
    )

    expected_nb_params = {"prefix": "10.1.111.0/24", "status": "active", "site": "a325e477-62fe-47f0-8b67-acf411b1868f"}
    nb_params = prefix.translate_attrs_for_nautobot(attrs=dict(vlan="HQ__112"))

    assert nb_params == expected_nb_params


def test_create_prefix(requests_mock, nautobot_api_base):
    data = yaml.safe_load(open(f"{ROOT}/../fixtures/prefix_no_vlan.json"))

    requests_mock.post("http://mock_nautobot/api/ipam/prefixes/", json=data, status_code=201)
    ip_address = NautobotPrefix.create(
        diffsync=nautobot_api_base, ids=dict(prefix="10.1.111.0/24", site_name="HQ"), attrs={}
    )

    assert isinstance(ip_address, NautobotPrefix) is True
    assert ip_address.remote_id == "3e1d0bf7-43de-493e-901e-661647aac2af"
    assert ip_address.vlan is None


def test_update_prefix(requests_mock, nautobot_api_base):
    data_no_vlan = yaml.safe_load(open(f"{ROOT}/../fixtures/prefix_no_vlan.json"))
    data_vlan = yaml.safe_load(open(f"{ROOT}/../fixtures/prefix_vlan.json"))

    remote_id = data_no_vlan["id"]

    requests_mock.get(f"http://mock_nautobot/api/ipam/prefixes/{remote_id}/", json=data_no_vlan, status_code=200)
    requests_mock.patch(f"http://mock_nautobot/api/ipam/prefixes/{remote_id}/", json=data_vlan, status_code=200)
    prefix = NautobotPrefix(diffsync=nautobot_api_base, prefix="10.1.111.0/24", site_name="HQ", remote_id=remote_id)

    prefix.update(attrs=dict(vlan="HQ__111"))
    assert prefix.vlan == "HQ__111"


def test_create_prefix_with_vlan(requests_mock, nautobot_api_base):
    data = yaml.safe_load(open(f"{ROOT}/../fixtures/prefix_vlan.json"))

    requests_mock.post("http://mock_nautobot/api/ipam/prefixes/", json=data, status_code=201)
    prefix = NautobotPrefix.create(
        diffsync=nautobot_api_base, ids=dict(prefix="10.1.111.0/24", site_name="HQ"), attrs=dict(vlan="HQ__111")
    )

    assert isinstance(prefix, NautobotPrefix) is True
    assert prefix.remote_id == "71d0b310-f32b-4cc0-b940-afb8ab50b985"
    assert prefix.vlan == "HQ__111"


def test_translate_attrs_for_nautobot_w_vlan(nautobot_api_base):
    prefix = NautobotPrefix(
        diffsync=nautobot_api_base,
        prefix="10.1.111.0/24",
        site_name="HQ",
        remote_id="171f82fc-8ab8-4840-9ae3-8337821be2fb",
    )
    nautobot_api_base.add(prefix)

    params = prefix.translate_attrs_for_nautobot({"vlan": "HQ__111"})

    assert "prefix" in params
    assert params["site"] == "a325e477-62fe-47f0-8b67-acf411b1868f"
    assert params["vlan"] == "464a2de3-fd5e-4b65-a58d-e0a2a617c12e"


def test_translate_attrs_for_nautobot_wo_vlan(nautobot_api_base):
    prefix = NautobotPrefix(
        diffsync=nautobot_api_base,
        prefix="10.1.111.0/24",
        site_name="HQ",
        remote_id="171f82fc-8ab8-4840-9ae3-8337821be2fb",
    )
    nautobot_api_base.add(prefix)

    params = prefix.translate_attrs_for_nautobot({"vlan": None})

    assert "prefix" in params
    assert params["site"] == "a325e477-62fe-47f0-8b67-acf411b1868f"
    assert "vlan" not in params
