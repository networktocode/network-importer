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
from network_importer.inventory import NBInventory

HERE = path.abspath(path.dirname(__file__))
FIXTURES = "config/fixtures/NBInventory"


def test_nb_inventory_all(requests_mock):
    """
    Test netbox dynamic inventory without filter parameters

    Args:
        requests_mock (:obj:`requests_mock.mocker.Mocker`): Automatically inserted
        by pytest library, mocks requests get to external API so external API call is
        not needed for unit test.
    """

    # Load mock data fixtures
    data1 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/devices.json"))
    requests_mock.get("http://mock/api/dcim/devices/", json=data1)

    data2 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/platforms.json"))
    requests_mock.get("http://mock/api/dcim/platforms/", json=data2)

    inv = NBInventory(nb_url="http://mock", nb_token="12349askdnfanasdf")  # nosec

    assert len(inv.hosts.keys()) == 6


def test_nb_inventory_filtered(requests_mock):
    """
    Test netbox dynamic inventory with filter parameters

    Args:
        requests_mock (:obj:`requests_mock.mocker.Mocker`): Automatically inserted
        by pytest library, mocks requests get to external API so external API call is
        not needed for unit test.
    """

    # Load mock data fixtures
    data1 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/filtered_devices.json"))
    requests_mock.get("http://mock/api/dcim/devices/?name=el-paso", json=data1)

    data2 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/platforms.json"))
    requests_mock.get("http://mock/api/dcim/platforms/", json=data2)

    inv_filtered = NBInventory(  # nosec
        nb_url="http://mock",  # nosec
        nb_token="12349askdnfanasdf",  # nosec
        filter_parameters={"name": "el-paso"},  # nosec
    )  # nosec

    assert len(inv_filtered.hosts.keys()) == 1
    assert "el-paso" in inv_filtered.hosts.keys()
    assert "amarillo" not in inv_filtered.hosts.keys()


def test_nb_inventory_virtual_chassis(requests_mock):
    """
    Test netbox virtual_chassis attribute set correctly

    Args:
        requests_mock (:obj:`requests_mock.mocker.Mocker`): Automatically inserted
        by pytest library, mocks requests get to external API so external API call is
        not needed for unit test.
    """

    # Load mock data fixtures
    data1 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/stack_devices.json"))
    requests_mock.get("http://mock/api/dcim/devices/", json=data1)

    data2 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/platforms.json"))
    requests_mock.get("http://mock/api/dcim/platforms/", json=data2)

    inv = NBInventory(nb_url="http://mock", nb_token="12349askdnfanasdf")  # nosec

    assert len(inv.hosts.keys()) == 2
    assert "test_dev1_2" not in inv.hosts.keys()
    assert "test_dev1" in inv.hosts.keys()
    assert inv.hosts["test_dev1"].data["virtual_chassis"]
    assert not inv.hosts["amarillo"].data["virtual_chassis"]
