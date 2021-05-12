"""test for NautobotInterface model."""
import os
import pytest

from diffsync.exceptions import ObjectNotFound

import network_importer.config as config
from network_importer.adapters.nautobot_api.models import NautobotInterface, NautobotDevice, NautobotVlan
from network_importer.adapters.nautobot_api.exceptions import NautobotObjectNotValid

ROOT = os.path.abspath(os.path.dirname(__file__))

# pylint: disable=pointless-statement


def assert_baseline(data):
    """Check that name and device are always present in the response."""
    assert "name" in data
    assert data["name"] == "ge-0/0/0"
    assert "device" in data
    assert data["device"] == 29


def test_translate_attrs_for_nautobot_wrong_device(nautobot_api_base):

    intf = NautobotInterface(device_name="HQ-CORE-SW01", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    with pytest.raises(ObjectNotFound):
        intf.translate_attrs_for_nautobot({})


def test_translate_attrs_for_nautobot_device_no_remote_id(nautobot_api_base):

    nautobot_api_base.add(NautobotDevice(name="HQ-CORE-SW01", site_name="nyc"))
    intf = NautobotInterface(device_name="HQ-CORE-SW01", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    with pytest.raises(NautobotObjectNotValid):
        intf.translate_attrs_for_nautobot({})


def test_translate_attrs_for_nautobot_no_attrs(nautobot_api_base):

    config.load(config_data=dict(main=dict(import_vlans=True)))
    intf = NautobotInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    params = intf.translate_attrs_for_nautobot({})

    assert sorted(list(params.keys())) == ["description", "device", "lag", "name", "type"]
    assert params["name"] == "ge-0/0/0"
    assert params["device"] == "e0633a07-c3e2-41b0-a1df-4627392acf0a"
    assert params["type"] == "other"
    assert params["lag"] is None
    assert params["description"] == ""


def test_translate_attrs_for_nautobot_type(nautobot_api_base):

    config.load(config_data=dict(main=dict(import_vlans=True)))
    intf = NautobotInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    params = intf.translate_attrs_for_nautobot({"is_lag": True, "is_virtual": True})
    assert_baseline
    assert params["type"] == "lag"

    params = intf.translate_attrs_for_nautobot({"is_lag": False, "is_virtual": True})
    assert_baseline
    assert params["type"] == "virtual"

    params = intf.translate_attrs_for_nautobot({"is_lag": False, "is_virtual": False})
    assert_baseline
    assert params["type"] == "other"


def test_translate_attrs_for_nautobot_description(nautobot_api_base):

    config.load(config_data=dict(main=dict(import_vlans=True)))
    intf = NautobotInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    params = intf.translate_attrs_for_nautobot({})
    assert_baseline
    assert "description" in params
    assert params["description"] == ""

    params = intf.translate_attrs_for_nautobot({"description": "my_description"})
    assert_baseline
    assert params["description"] == "my_description"

    params = intf.translate_attrs_for_nautobot({"description": None})
    assert_baseline
    assert params["description"] == ""
    assert isinstance(params["description"], str)


def test_translate_attrs_for_nautobot_mode(nautobot_api_base):

    config.load(config_data=dict(main=dict(import_vlans=True)))
    intf = NautobotInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    params = intf.translate_attrs_for_nautobot({})
    assert_baseline
    assert "mode" not in params

    params = intf.translate_attrs_for_nautobot({"switchport_mode": "ACCESS"})
    assert_baseline
    assert params["mode"] == "access"

    params = intf.translate_attrs_for_nautobot({"switchport_mode": "TRUNK"})
    assert_baseline
    assert params["mode"] == "tagged"

    params = intf.translate_attrs_for_nautobot({"switchport_mode": "NOTSUPPORTED"})
    assert_baseline
    assert "mode" not in params


def test_translate_attrs_for_nautobot_vlan(nautobot_api_base):

    vlan = NautobotVlan(vid=100, site_name="HQ", remote_id="601077ce-ac88-4b36-bbc7-23d655dc3958")
    nautobot_api_base.add(vlan)

    config.load(config_data=dict(main=dict(import_vlans=True)))
    intf = NautobotInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    params = intf.translate_attrs_for_nautobot({})
    assert_baseline
    assert "mode" not in params

    params = intf.translate_attrs_for_nautobot(
        {"switchport_mode": "ACCESS", "mode": "ACCESS", "access_vlan": "HQ__111"}
    )
    assert_baseline
    assert params["mode"] == "access"
    assert params["untagged_vlan"] == "464a2de3-fd5e-4b65-a58d-e0a2a617c12e"

    params = intf.translate_attrs_for_nautobot({"switchport_mode": "ACCESS", "mode": "ACCESS", "access_vlan": None})
    assert_baseline
    assert params["mode"] == "access"
    assert params["untagged_vlan"] is None

    params = intf.translate_attrs_for_nautobot({"switchport_mode": "ACCESS", "mode": "ACCESS"})
    assert_baseline
    assert params["mode"] == "access"
    assert params["untagged_vlan"] is None

    params = intf.translate_attrs_for_nautobot(
        {"switchport_mode": "TRUNK", "mode": "TRUNK", "allowed_vlans": ["HQ__111", "HQ__100"]}
    )
    assert_baseline
    assert params["mode"] == "tagged"
    assert params["tagged_vlans"] == ["464a2de3-fd5e-4b65-a58d-e0a2a617c12e", "601077ce-ac88-4b36-bbc7-23d655dc3958"]

    params = intf.translate_attrs_for_nautobot({"switchport_mode": "TRUNK", "mode": "TRUNK"})
    assert_baseline
    assert params["mode"] == "tagged"
    assert params["tagged_vlans"] == []

    params = intf.translate_attrs_for_nautobot({"switchport_mode": "TRUNK", "mode": "L3_SUB_VLAN"})
    assert_baseline
    assert params["mode"] == "tagged"
    assert params["tagged_vlans"] == []


def test_translate_attrs_for_nautobot_vlan_false(nautobot_api_base):

    config.load(config_data=dict(main=dict(import_vlans=False)))
    intf = NautobotInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    params = intf.translate_attrs_for_nautobot(
        {"switchport_mode": "TRUNK", "mode": "TRUNK", "allowed_vlans": ["HQ__111", "HQ__100"]}
    )
    assert_baseline
    assert "tagged_vlans" not in params
    assert "untagged_vlan" not in params

    params = intf.translate_attrs_for_nautobot(
        {"switchport_mode": "ACCESS", "mode": "ACCESS", "access_vlan": "HQ__111"}
    )
    assert_baseline
    assert "tagged_vlans" not in params
    assert "untagged_vlan" not in params


def test_translate_attrs_for_nautobot_vlan_no(nautobot_api_base):

    config.load(config_data=dict(main=dict(import_vlans="no")))
    intf = NautobotInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    params = intf.translate_attrs_for_nautobot(
        {"switchport_mode": "TRUNK", "mode": "TRUNK", "allowed_vlans": ["HQ__111", "HQ__100"]}
    )
    assert_baseline
    assert "tagged_vlans" not in params
    assert "untagged_vlan" not in params

    params = intf.translate_attrs_for_nautobot(
        {"switchport_mode": "ACCESS", "mode": "ACCESS", "access_vlan": "HQ__111"}
    )
    assert_baseline
    assert "tagged_vlans" not in params
    assert "untagged_vlan" not in params


def test_translate_attrs_for_nautobot_lag_member(nautobot_api_base):

    parent = NautobotInterface(
        device_name="HQ-CORE-SW01", name="ge-0/0/4", remote_id="ea085648-5684-4362-a8dd-edfa151faaec"
    )
    nautobot_api_base.add(parent)

    config.load(config_data=dict(main=dict(import_vlans=False)))
    intf = NautobotInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    nautobot_api_base.add(intf)

    params = intf.translate_attrs_for_nautobot({"is_lag_member": True, "parent": "HQ-CORE-SW01__ge-0/0/4"})
    assert_baseline
    assert "lag" in params
    assert params["lag"] == "ea085648-5684-4362-a8dd-edfa151faaec"

    params = intf.translate_attrs_for_nautobot({"is_lag_member": False, "parent": "HQ-CORE-SW01__ge-0/0/4"})
    assert_baseline
    assert "lag" in params
    assert params["lag"] is None
