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
import pynetbox

from network_importer.adapters.netbox_api.models import NetboxIPAddressPre29

ROOT = os.path.abspath(os.path.dirname(__file__))


def test_translate_attrs_for_netbox_with_intf(netbox_api_base):

    ipaddr = NetboxIPAddressPre29(
        address="10.10.10.1/24", device_name="HQ-CORE-SW02", interface_name="TenGigabitEthernet1/0/2", remote_id=30
    )
    netbox_api_base.add(ipaddr)

    params = ipaddr.translate_attrs_for_netbox(
        attrs=dict(device_name="HQ-CORE-SW02", interface_name="TenGigabitEthernet1/0/1")
    )

    assert "address" in params
    assert params["address"] == "10.10.10.1/24"
    assert "interface" in params
    assert params["interface"] == 302


def test_translate_attrs_for_netbox_wo_intf(netbox_api_base):

    ipaddr = NetboxIPAddressPre29(
        address="10.10.10.1/24", device_name="HQ-CORE-SW02", interface_name="TenGigabitEthernet1/0/2", remote_id=30
    )
    netbox_api_base.add(ipaddr)

    params = ipaddr.translate_attrs_for_netbox(attrs={})

    assert "address" in params
    assert params["address"] == "10.10.10.1/24"
    assert "interface" not in params


def test_create_from_pynetbox(netbox_api_base):

    api = pynetbox.api(url="http://mock", token="1234567890")
    data = yaml.safe_load(open(f"{ROOT}/../fixtures/netbox_28/ip_address.json"))
    pnb = pynetbox.core.response.Record(values=data, api=api, endpoint=1)

    ipaddr = NetboxIPAddressPre29.create_from_pynetbox(diffsync=netbox_api_base, obj=pnb, device_name="HQ-CORE-SW02")

    assert ipaddr.interface_name == "TenGigabitEthernet1/0/1"
    assert ipaddr.device_name == "HQ-CORE-SW02"
