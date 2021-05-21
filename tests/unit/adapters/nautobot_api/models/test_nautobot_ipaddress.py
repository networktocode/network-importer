"""test for NautobotIPAddress model."""
import os
import yaml
import pynautobot

from network_importer.adapters.nautobot_api.models import NautobotIPAddress

ROOT = os.path.abspath(os.path.dirname(__file__))


def test_translate_attrs_for_nautobot_with_intf(nautobot_api_base):

    ipaddr = NautobotIPAddress(
        address="10.10.10.1/24",
        device_name="HQ-CORE-SW02",
        interface_name="TenGigabitEthernet1/0/1",
        remote_id="2c6f4d82-e8e4-48ca-a62f-abf8586ff82a",
    )
    nautobot_api_base.add(ipaddr)
    params = ipaddr.translate_attrs_for_nautobot()

    assert "address" in params
    assert params["address"] == "10.10.10.1/24"
    assert "assigned_object_type" in params
    assert params["assigned_object_type"] == "dcim.interface"
    assert "assigned_object_id" in params
    assert params["assigned_object_id"] == "fecc1d8f-99b1-491d-9bdf-1dcb394e27a1"


def test_translate_attrs_for_nautobot_wo_intf(nautobot_api_base):

    ipaddr = NautobotIPAddress(
        address="10.10.10.1/24",
        device_name="HQ-CORE-SW02",
        interface_name="TenGigabitEthernet1/0/2",
        remote_id="2c6f4d82-e8e4-48ca-a62f-abf8586ff82a",
    )
    nautobot_api_base.add(ipaddr)
    params = ipaddr.translate_attrs_for_nautobot()

    assert "address" in params
    assert params["address"] == "10.10.10.1/24"
    assert "assigned_object_type" not in params
    assert "assigned_object_id" not in params


def test_create_from_pynautobot(nautobot_api_base):
    api = pynautobot.api(url="http://mock", token="1234567890")
    data = yaml.safe_load(open(f"{ROOT}/../fixtures/ip_address.json"))
    pnb = pynautobot.core.response.Record(values=data, api=api, endpoint=1)

    ipaddr = NautobotIPAddress.create_from_pynautobot(diffsync=nautobot_api_base, obj=pnb, device_name="HQ-CORE-SW02")

    assert ipaddr.interface_name == "TenGigabitEthernet1/0/1"
    assert ipaddr.device_name == "HQ-CORE-SW02"


def test_create_ip_address_interface(requests_mock, nautobot_api_base):

    with open(f"{ROOT}/../fixtures/ip_address.json") as file:
        data = yaml.safe_load(file)

    requests_mock.post("http://mock_nautobot/api/ipam/ip-addresses/", json=data, status_code=201)
    ip_address = NautobotIPAddress.create(
        diffsync=nautobot_api_base,
        ids=dict(address="10.63.0.2/31", interface_name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02"),
        attrs=dict(),
    )

    assert isinstance(ip_address, NautobotIPAddress) is True
    assert ip_address.remote_id == "2c6f4d82-e8e4-48ca-a62f-abf8586ff82a"


def test_create_ip_address_no_interface(requests_mock, nautobot_api_base):

    with open(f"{ROOT}/../fixtures/ip_address.json") as file:
        data = yaml.safe_load(file)

    requests_mock.post("http://mock_nautobot/api/ipam/ip-addresses/", json=data, status_code=201)
    ip_address = NautobotIPAddress.create(
        diffsync=nautobot_api_base,
        ids=dict(address="10.63.0.2/31", interface_name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02"),
        attrs=dict(),
    )

    assert isinstance(ip_address, NautobotIPAddress) is True
    assert ip_address.remote_id == "2c6f4d82-e8e4-48ca-a62f-abf8586ff82a"
