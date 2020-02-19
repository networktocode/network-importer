"""
(c) 2019 Network To Code

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

from os import path
import yaml
import network_importer.config as config
from network_importer.inventory import NBInventory

HERE = path.abspath(path.dirname(__file__))
FIXTURES = "config/fixtures/NBInventory"


def test_nb_inventory(requests_mock):
    """
    Test netbox dynamic inventory filter parameters
    """

    # Load config data, needed by NBInventory function
    config.load_config()

    # Load mock data fixtures
    dev_mock_data = yaml.safe_load(open(f"{HERE}/{FIXTURES}/devices.json"))
    dev_filtered_mock_data = yaml.safe_load(
        open(f"{HERE}/{FIXTURES}/filtered_devices.json")
    )

    # Set up mock requests
    requests_mock.get("http://mock/api/dcim/devices/", json=dev_mock_data)
    requests_mock.get(
        "http://mock/api/dcim/devices/?name=el-paso", json=dev_filtered_mock_data
    )

    inv = NBInventory(nb_url="http://mock", nb_token="12349askdnfanasdf")  # nosec

    inv_filtered = NBInventory(  # nosec
        nb_url="http://mock",  # nosec
        nb_token="12349askdnfanasdf",  # nosec
        filter_parameters={"name": "el-paso"},  # nosec
    )  # nosec

    assert len(inv.hosts.keys()) == 6
    assert len(inv_filtered.hosts.keys()) == 1
    assert "el-paso" in inv_filtered.hosts.keys()
    assert "amarillo" not in inv_filtered.hosts.keys()
