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
# pylint: disable=E1101

from os import path
import yaml
from network_importer.adapters.netbox_api.inventory import NetBoxAPIInventory

HERE = path.abspath(path.dirname(__file__))
FIXTURES = "fixtures/inventory"


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
    requests_mock.get("http://mock/api/dcim/devices/?exclude=config_context", json=data1)

    data2 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/platforms.json"))
    requests_mock.get("http://mock/api/dcim/platforms/", json=data2)

    inv = NetBoxAPIInventory(settings=dict(address="http://mock", token="12349askdnfanasdf")).load()  # nosec

    assert len(inv.hosts.keys()) == 6
    assert "austin" in inv.hosts.keys()
    assert inv.hosts["austin"].platform == "ios"
    assert inv.hosts["austin"].connection_options["napalm"].platform == "ios_naplam"
    assert "dallas" in inv.hosts.keys()
    assert inv.hosts["dallas"].platform == "nxos"
    assert inv.hosts["dallas"].connection_options["napalm"].platform == "nxos_naplam"
    assert "el-paso" in inv.hosts.keys()
    assert inv.hosts["el-paso"].platform == "asa"


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
    requests_mock.get("http://mock/api/dcim/devices/?name=el-paso&exclude=config_context", json=data1)

    data2 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/platforms.json"))
    requests_mock.get("http://mock/api/dcim/platforms/", json=data2)

    inv_filtered = NetBoxAPIInventory(
        limit="el-paso", settings=dict(address="http://mock", token="12349askdnfanasdf",)  # nosec
    ).load()  # nosec

    assert len(inv_filtered.hosts.keys()) == 1
    assert "el-paso" in inv_filtered.hosts.keys()
    assert "amarillo" not in inv_filtered.hosts.keys()


def test_nb_inventory_exclude(requests_mock):
    """
    Test netbox dynamic inventory with exclude filter parameters

    Args:
        requests_mock (:obj:`requests_mock.mocker.Mocker`): Automatically inserted
        by pytest library, mocks requests get to external API so external API call is
        not needed for unit test.
    """

    # Load mock data fixtures
    data1 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/devices.json"))
    requests_mock.get("http://mock/api/dcim/devices/?exclude=platform", json=data1)

    data2 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/platforms.json"))
    requests_mock.get("http://mock/api/dcim/platforms/", json=data2)

    inv = NetBoxAPIInventory(
        settings=dict(address="http://mock", token="12349askdnfanasdf", filter="exclude=platform",)  # nosec  # nosec
    ).load()  # nosec

    assert len(inv.hosts.keys()) == 6


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

    inv = NetBoxAPIInventory(settings=dict(address="http://mock", token="12349askdnfanasdf")).load()  # nosec

    assert len(inv.hosts.keys()) == 2
    assert "test_dev1_2" not in inv.hosts.keys()
    assert "test_dev1" in inv.hosts.keys()
    assert inv.hosts["test_dev1"].data["virtual_chassis"]
    assert not inv.hosts["amarillo"].data["virtual_chassis"]


def test_nb_inventory_supported_platforms(requests_mock):
    """
    Test netbox dynamic inventory with a list of supported platforms

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

    inv = NetBoxAPIInventory(
        supported_platforms=["ios", "nxos"],  # nosec
        settings=dict(address="http://mock", token="12349askdnfanasdf")  # nosec  # nosec
        # nosec
    ).load()  # nosec

    assert len(inv.hosts.keys()) == 2
    assert "austin" in inv.hosts.keys()
    assert "dallas" in inv.hosts.keys()

    inv = NetBoxAPIInventory(  # nosec
        supported_platforms=["ios"], settings=dict(address="http://mock", token="12349askdnfanasdf")  # nosec
    ).load()  # nosec

    assert len(inv.hosts.keys()) == 1
    assert "austin" in inv.hosts.keys()
    assert "dallas" not in inv.hosts.keys()
