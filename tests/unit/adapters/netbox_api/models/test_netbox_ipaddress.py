"""test for NetboxIPAddress model."""
import os
import yaml
import pynetbox

from network_importer.adapters.netbox_api.models import NetboxIPAddress

ROOT = os.path.abspath(os.path.dirname(__file__))


def test_translate_attrs_for_netbox_with_intf(netbox_api_base):
    ipaddr = NetboxIPAddress(
        address="10.10.10.1/24", device_name="HQ-CORE-SW02", interface_name="TenGigabitEthernet1/0/1", remote_id=302
    )
    netbox_api_base.add(ipaddr)
    params = ipaddr.translate_attrs_for_netbox()

    assert "address" in params
    assert params["address"] == "10.10.10.1/24"
    assert "assigned_object_type" in params
    assert params["assigned_object_type"] == "dcim.interface"
    assert "assigned_object_id" in params
    assert params["assigned_object_id"] == 302


def test_translate_attrs_for_netbox_wo_intf(netbox_api_base):
    ipaddr = NetboxIPAddress(
        address="10.10.10.1/24", device_name="HQ-CORE-SW02", interface_name="TenGigabitEthernet1/0/2", remote_id=302
    )
    netbox_api_base.add(ipaddr)
    params = ipaddr.translate_attrs_for_netbox()

    assert "address" in params
    assert params["address"] == "10.10.10.1/24"
    assert "assigned_object_type" not in params
    assert "assigned_object_id" not in params


def test_create_from_pynetbox(netbox_api_base):
    api = pynetbox.api(url="http://mock", token="1234567890")
    data = yaml.safe_load(open(f"{ROOT}/../fixtures/netbox_29/ip_address.json"))
    pnb = pynetbox.core.response.Record(values=data, api=api, endpoint=1)

    ipaddr = NetboxIPAddress.create_from_pynetbox(diffsync=netbox_api_base, obj=pnb, device_name="HQ-CORE-SW02")

    assert ipaddr.interface_name == "TenGigabitEthernet1/0/1"
    assert ipaddr.device_name == "HQ-CORE-SW02"


def test_create_ip_address_interface(requests_mock, netbox_api_base):
    with open(f"{ROOT}/../fixtures/netbox_28/ip_address.json") as file:
        data = yaml.safe_load(file)

    requests_mock.post("http://mock/api/ipam/ip-addresses/", json=data, status_code=201)
    ip_address = NetboxIPAddress.create(
        diffsync=netbox_api_base,
        ids=dict(address="10.63.0.2/31", interface_name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02"),
        attrs=dict(),
    )

    assert isinstance(ip_address, NetboxIPAddress) is True
    assert ip_address.remote_id == 15


def test_create_ip_address_no_interface(requests_mock, netbox_api_base):
    with open(f"{ROOT}/../fixtures/netbox_28/ip_address.json") as file:
        data = yaml.safe_load(file)

    requests_mock.post("http://mock/api/ipam/ip-addresses/", json=data, status_code=201)
    ip_address = NetboxIPAddress.create(
        diffsync=netbox_api_base,
        ids=dict(address="10.63.0.2/31", interface_name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02"),
        attrs=dict(),
    )

    assert isinstance(ip_address, NetboxIPAddress) is True
    assert ip_address.remote_id == 15
