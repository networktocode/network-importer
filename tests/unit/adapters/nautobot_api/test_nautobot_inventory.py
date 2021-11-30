"""test for NautobotAPI Inventory."""
# pylint: disable=E1101

from os import path
import yaml
from network_importer.adapters.nautobot_api.inventory import NautobotAPIInventory

HERE = path.abspath(path.dirname(__file__))
FIXTURES = "fixtures/inventory"


def test_nautobot_inventory_all(requests_mock):
    """
    Test nautobot dynamic inventory without filter parameters

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

    inv = NautobotAPIInventory(
        settings=dict(address="http://mock", token="12349askdnfanasdf"),
    ).load()  # nosec

    assert len(inv.hosts.keys()) == 3
    assert "grb-rtr01" in inv.hosts.keys()
    assert inv.hosts["grb-rtr01"].platform == "ios"
    assert "msp-rtr01" in inv.hosts.keys()
    assert inv.hosts["msp-rtr01"].platform == "nxos"
    assert inv.hosts["msp-rtr01"].connection_options["napalm"].platform == "nxos_napalm"
    assert "sw01" in inv.hosts.keys()
    assert inv.hosts["sw01"].platform == "cisco_ios"
    assert inv.hosts["sw01"].connection_options["napalm"].platform == "ios"


def test_nb_inventory_filtered(requests_mock):
    """
    Test nautobot dynamic inventory with filter parameters

    Args:
        requests_mock (:obj:`requests_mock.mocker.Mocker`): Automatically inserted
        by pytest library, mocks requests get to external API so external API call is
        not needed for unit test.
    """
    # Load mock data fixtures
    data1 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/filtered_devices.json"))
    requests_mock.get("http://mock/api/dcim/devices/?name=grb-rtr01&exclude=config_context", json=data1)

    data2 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/platforms.json"))
    requests_mock.get("http://mock/api/dcim/platforms/", json=data2)

    inv_filtered = NautobotAPIInventory(
        limit="grb-rtr01",
        settings=dict(
            address="http://mock",
            token="12349askdnfanasdf",
        ),  # nosec
    ).load()  # nosec

    assert len(inv_filtered.hosts.keys()) == 1
    assert "grb-rtr01" in inv_filtered.hosts.keys()
    assert "msp-rtr01" not in inv_filtered.hosts.keys()


def test_nb_inventory_exclude(requests_mock):
    """
    Test nautobot dynamic inventory with exclude filter parameters

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

    inv = NautobotAPIInventory(
        settings=dict(
            address="http://mock",
            token="12349askdnfanasdf",
            filter="exclude=platform",
        ),  # nosec  # nosec
    ).load()  # nosec

    assert len(inv.hosts.keys()) == 3


def test_nb_inventory_virtual_chassis(requests_mock):
    """
    Test nautobot virtual_chassis attribute set correctly

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

    inv = NautobotAPIInventory(
        username="mock",
        password="mock",
        enable="mock",
        supported_platforms=["cisco_ios", "nxos", "ios"],
        limit=None,
        settings=dict(address="http://mock", token="12349askdnfanasdf"),
    ).load()  # nosec

    assert len(inv.hosts.keys()) == 4
    assert "stack01:2" not in inv.hosts.keys()
    assert "stack01" in inv.hosts.keys()
    assert inv.hosts["stack01"].data["virtual_chassis"]
    assert not inv.hosts["msp-rtr01"].data["virtual_chassis"]


def test_nb_inventory_supported_platforms(requests_mock):
    """
    Test nautobot dynamic inventory with a list of supported platforms

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

    inv = NautobotAPIInventory(
        supported_platforms=["ios", "nxos"],
        settings=dict(address="http://mock", token="12349askdnfanasdf")  # nosec  # nosec
        # nosec
    ).load()  # nosec

    assert len(inv.hosts.keys()) == 2
    assert "grb-rtr01" in inv.hosts.keys()
    assert "msp-rtr01" in inv.hosts.keys()
    assert "sw01" not in inv.hosts.keys()

    inv = NautobotAPIInventory(  # nosec
        username="mock",
        password="mock",
        enable="mock",
        limit=None,
        supported_platforms=["ios"],
        settings=dict(address="http://mock", token="12349askdnfanasdf"),  # nosec
    ).load()  # nosec

    assert len(inv.hosts.keys()) == 1
    assert "grb-rtr01" in inv.hosts.keys()
    assert "msp-rtr01" not in inv.hosts.keys()
    assert "sw01" not in inv.hosts.keys()
