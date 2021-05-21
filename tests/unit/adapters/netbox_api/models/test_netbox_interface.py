"""test for NetboxInterface model."""
import os
import pytest

from diffsync.exceptions import ObjectNotFound

import network_importer.config as config
from network_importer.adapters.netbox_api.models import NetboxInterface, NetboxDevice, NetboxVlan
from network_importer.adapters.netbox_api.exceptions import NetboxObjectNotValid

ROOT = os.path.abspath(os.path.dirname(__file__))
FIXTURE_28 = "../fixtures/netbox_28"
FIXTURE_29 = "../fixtures/netbox_29"

# pylint: disable=pointless-statement


def assert_baseline(data):
    """Check that name and device are always present in the response."""
    assert "name" in data
    assert data["name"] == "ge-0/0/0"
    assert "device" in data
    assert data["device"] == 29


def test_translate_attrs_for_netbox_wrong_device(netbox_api_base):

    intf = NetboxInterface(device_name="HQ-CORE-SW01", name="ge-0/0/0")
    netbox_api_base.add(intf)

    with pytest.raises(ObjectNotFound):
        intf.translate_attrs_for_netbox({})


def test_translate_attrs_for_netbox_device_no_remote_id(netbox_api_base):

    netbox_api_base.add(NetboxDevice(name="HQ-CORE-SW01", site_name="nyc"))
    intf = NetboxInterface(device_name="HQ-CORE-SW01", name="ge-0/0/0")
    netbox_api_base.add(intf)

    with pytest.raises(NetboxObjectNotValid):
        intf.translate_attrs_for_netbox({})


def test_translate_attrs_for_netbox_no_attrs(netbox_api_base):

    config.load(config_data=dict(main=dict(import_vlans=True, backend="netbox")))
    intf = NetboxInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    netbox_api_base.add(intf)

    params = intf.translate_attrs_for_netbox({})

    assert sorted(list(params.keys())) == ["description", "device", "lag", "name", "type"]
    assert params["name"] == "ge-0/0/0"
    assert params["device"] == 29
    assert params["type"] == "other"
    assert params["lag"] is None
    assert params["description"] == ""


def test_translate_attrs_for_netbox_type(netbox_api_base):

    config.load(config_data=dict(main=dict(import_vlans=True, backend="netbox")))
    intf = NetboxInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    netbox_api_base.add(intf)

    params = intf.translate_attrs_for_netbox({"is_lag": True, "is_virtual": True})
    assert_baseline
    assert params["type"] == "lag"

    params = intf.translate_attrs_for_netbox({"is_lag": False, "is_virtual": True})
    assert_baseline
    assert params["type"] == "virtual"

    params = intf.translate_attrs_for_netbox({"is_lag": False, "is_virtual": False})
    assert_baseline
    assert params["type"] == "other"


def test_translate_attrs_for_netbox_description(netbox_api_base):

    config.load(config_data=dict(main=dict(import_vlans=True, backend="netbox")))
    intf = NetboxInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    netbox_api_base.add(intf)

    params = intf.translate_attrs_for_netbox({})
    assert_baseline
    assert "description" in params
    assert params["description"] == ""

    params = intf.translate_attrs_for_netbox({"description": "my_description"})
    assert_baseline
    assert params["description"] == "my_description"

    params = intf.translate_attrs_for_netbox({"description": None})
    assert_baseline
    assert params["description"] == ""
    assert isinstance(params["description"], str)


def test_translate_attrs_for_netbox_mode(netbox_api_base):

    config.load(config_data=dict(main=dict(import_vlans=True, backend="netbox")))
    intf = NetboxInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    netbox_api_base.add(intf)

    params = intf.translate_attrs_for_netbox({})
    assert_baseline
    assert "mode" not in params

    params = intf.translate_attrs_for_netbox({"switchport_mode": "ACCESS"})
    assert_baseline
    assert params["mode"] == "access"

    params = intf.translate_attrs_for_netbox({"switchport_mode": "TRUNK"})
    assert_baseline
    assert params["mode"] == "tagged"

    params = intf.translate_attrs_for_netbox({"switchport_mode": "NOTSUPPORTED"})
    assert_baseline
    assert "mode" not in params


def test_translate_attrs_for_netbox_vlan(netbox_api_base):

    vlan = NetboxVlan(vid=100, site_name="HQ", remote_id=30)
    netbox_api_base.add(vlan)

    config.load(config_data=dict(main=dict(import_vlans=True, backend="netbox")))
    intf = NetboxInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    netbox_api_base.add(intf)

    params = intf.translate_attrs_for_netbox({})
    assert_baseline
    assert "mode" not in params

    params = intf.translate_attrs_for_netbox({"switchport_mode": "ACCESS", "mode": "ACCESS", "access_vlan": "HQ__111"})
    assert_baseline
    assert params["mode"] == "access"
    assert params["untagged_vlan"] == 23

    params = intf.translate_attrs_for_netbox({"switchport_mode": "ACCESS", "mode": "ACCESS", "access_vlan": None})
    assert_baseline
    assert params["mode"] == "access"
    assert params["untagged_vlan"] is None

    params = intf.translate_attrs_for_netbox({"switchport_mode": "ACCESS", "mode": "ACCESS"})
    assert_baseline
    assert params["mode"] == "access"
    assert params["untagged_vlan"] is None

    params = intf.translate_attrs_for_netbox(
        {"switchport_mode": "TRUNK", "mode": "TRUNK", "allowed_vlans": ["HQ__111", "HQ__100"]}
    )
    assert_baseline
    assert params["mode"] == "tagged"
    assert params["tagged_vlans"] == [23, 30]

    params = intf.translate_attrs_for_netbox({"switchport_mode": "TRUNK", "mode": "TRUNK"})
    assert_baseline
    assert params["mode"] == "tagged"
    assert params["tagged_vlans"] == []

    params = intf.translate_attrs_for_netbox({"switchport_mode": "TRUNK", "mode": "L3_SUB_VLAN"})
    assert_baseline
    assert params["mode"] == "tagged"
    assert params["tagged_vlans"] == []


def test_translate_attrs_for_netbox_vlan_false(netbox_api_base):

    config.load(config_data=dict(main=dict(import_vlans=False, backend="netbox")))
    intf = NetboxInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    netbox_api_base.add(intf)

    params = intf.translate_attrs_for_netbox(
        {"switchport_mode": "TRUNK", "mode": "TRUNK", "allowed_vlans": ["HQ__111", "HQ__100"]}
    )
    assert_baseline
    assert "tagged_vlans" not in params
    assert "untagged_vlan" not in params

    params = intf.translate_attrs_for_netbox({"switchport_mode": "ACCESS", "mode": "ACCESS", "access_vlan": "HQ__111"})
    assert_baseline
    assert "tagged_vlans" not in params
    assert "untagged_vlan" not in params


def test_translate_attrs_for_netbox_vlan_no(netbox_api_base):

    config.load(config_data=dict(main=dict(import_vlans="no", backend="netbox")))
    intf = NetboxInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    netbox_api_base.add(intf)

    params = intf.translate_attrs_for_netbox(
        {"switchport_mode": "TRUNK", "mode": "TRUNK", "allowed_vlans": ["HQ__111", "HQ__100"]}
    )
    assert_baseline
    assert "tagged_vlans" not in params
    assert "untagged_vlan" not in params

    params = intf.translate_attrs_for_netbox({"switchport_mode": "ACCESS", "mode": "ACCESS", "access_vlan": "HQ__111"})
    assert_baseline
    assert "tagged_vlans" not in params
    assert "untagged_vlan" not in params


def test_translate_attrs_for_netbox_lag_member(netbox_api_base):

    parent = NetboxInterface(device_name="HQ-CORE-SW01", name="ge-0/0/4", remote_id=50)
    netbox_api_base.add(parent)

    config.load(config_data=dict(main=dict(import_vlans=False, backend="netbox")))
    intf = NetboxInterface(device_name="HQ-CORE-SW02", name="ge-0/0/0")
    netbox_api_base.add(intf)

    params = intf.translate_attrs_for_netbox({"is_lag_member": True, "parent": "HQ-CORE-SW01__ge-0/0/4"})
    assert_baseline
    assert "lag" in params
    assert params["lag"] == 50

    params = intf.translate_attrs_for_netbox({"is_lag_member": False, "parent": "HQ-CORE-SW01__ge-0/0/4"})
    assert_baseline
    assert "lag" in params
    assert params["lag"] is None
