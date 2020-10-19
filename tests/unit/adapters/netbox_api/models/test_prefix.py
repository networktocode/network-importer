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

from network_importer.adapters.netbox_api.models import NetboxPrefix

ROOT = os.path.abspath(os.path.dirname(__file__))


def test_create_prefix(requests_mock, netbox_api_base):

    with open(f"{ROOT}/../fixtures/netbox_28/prefix_no_vlan.json") as file:
        data = yaml.safe_load(file)

    requests_mock.post("http://mock/api/ipam/prefixes/", json=data, status_code=201)
    ip_address = NetboxPrefix.create(dsync=netbox_api_base, ids=dict(prefix="10.1.111.0/24", site_name="HQ"), attrs={})

    assert isinstance(ip_address, NetboxPrefix) is True
    assert ip_address.remote_id == 44
