"""Used to setup fixtures to be used through tests"""
import pytest

import pynetbox
import pynautobot
from diffsync import Adapter
from diffsync.diff import DiffElement

# from diffsync.exceptions import ObjectNotCreated, ObjectNotUpdated, ObjectNotDeleted

from network_importer.models import Site, Device, Interface, Vlan

from network_importer.adapters.network_importer.adapter import NetworkImporterAdapter

from network_importer.adapters.netbox_api.adapter import NetBoxAPIAdapter
from network_importer.adapters.netbox_api.models import NetboxSite, NetboxDevice, NetboxInterface, NetboxVlan

from network_importer.adapters.nautobot_api.adapter import NautobotAPIAdapter
from network_importer.adapters.nautobot_api.models import NautobotSite, NautobotDevice, NautobotInterface, NautobotVlan


@pytest.fixture
def make_site():
    """Factory for Site instances."""

    def site(name="site1", devices=None):
        """Provide an instance of a Site model."""
        if not devices:
            devices = []
        return Site(name=name, devices=devices)

    return site


@pytest.fixture
def make_device():
    """Factory for Device instances."""

    def device(name="device1", site_name="site1", **kwargs):
        """Provide an instance of a Device model."""
        return Device(name=name, site_name=site_name, **kwargs)

    return device


@pytest.fixture
def make_interface():
    """Factory for Interface instances."""

    def interface(device_name="device1", name="eth0", **kwargs):
        """Provide an instance of an Interface model."""
        return Interface(device_name=device_name, name=name, **kwargs)

    return interface


@pytest.fixture
def site_hq():
    """Fixture for a site named HQ."""
    return Site(name="HQ")


@pytest.fixture
def site_sfo():
    """Fixture for a site named SFO."""
    return Site(name="sfo")


@pytest.fixture
def dev_spine1():
    """Fixture for a device named spine1 as part of SFO."""
    return Device(name="spine1", site_name="sfo")


@pytest.fixture
def dev_spine2():
    """Fixture for a device named spine2 as part of SFO."""
    return Device(name="spine2", site_name="sfo")


class GenericBackend(Adapter):
    """An example semi-abstract subclass of DiffSync."""

    site = Site
    device = Device
    interface = Interface

    top_level = ["site"]

    DATA: dict = {}

    def load(self):
        """Initialize the Backend object by loading some site, device and interfaces from DATA."""
        for site_name, site_data in self.DATA.items():
            site = self.site(name=site_name)
            self.add(site)

            for device_name, device_data in site_data.items():
                device = self.device(name=device_name, role=device_data["role"], site_name=site_name)
                self.add(device)

                for intf_name, desc in device_data["interfaces"].items():
                    intf = self.interface(name=intf_name, device_name=device_name, description=desc)
                    self.add(intf)
                    device.add_child(intf)


class BackendA(GenericBackend):
    """An example concrete subclass of DiffSync."""

    DATA = {
        "nyc": {
            "nyc-dev1": {
                "interfaces": {
                    "ae0": {"description": "Lag 0", "is_lag": True},
                    "ae3": {"description": "Lag 3", "is_lag": True},
                    "eth0": {"description": "Interface 0", "is_lag_member": True, "parent": "ae0"},
                    "eth1": {"description": "Interface 1", "is_lag_member": True, "parent": "ae0"},
                    "eth2": {"description": "Interface 2"},
                }
            },
            "nyc-dev2": {
                "interfaces": {"eth0": {"description": "Interface 0"}, "eth1": {"description": "Interface 1"}}
            },
        },
        "sfo": {
            "sfo-dev1": {
                "interfaces": {"eth0": {"description": "Interface 0"}, "eth1": {"description": "not defined"}}
            },
            "sfo-dev2": {
                "interfaces": {
                    "eth0": {"description": "Interface 0"},
                    "eth1": {"description": "Interface 1"},
                    "eth2": {"description": "Interface 2"},
                }
            },
        },
    }


@pytest.fixture
def backend_a():
    """Provide an instance of BackendA subclass of DiffSync."""
    adapter = BackendA()
    adapter.load()
    return adapter


class BackendB(GenericBackend):
    """Another DiffSync concrete subclass with different data from BackendA."""

    DATA = {
        "nyc": {
            "nyc-dev1": {
                "interfaces": {
                    "ae0": {"description": "Lag 0", "is_lag": True},
                    "ae1": {"description": "Lag 1", "is_lag": True},
                    "eth0": {"description": "Interface 0", "is_lag_member": True, "parent": "ae0"},
                    "eth2": {"description": "Interface 2"},
                    "eth4": {"description": "Interface 4", "is_lag_member": True, "parent": "ae1"},
                }
            },
            "nyc-dev2": {
                "interfaces": {"eth0": {"description": "Interface 0"}, "eth1": {"description": "Interface 1"}}
            },
        },
        "sfo": {
            "sfo-dev1": {
                "interfaces": {"eth0": {"description": "Interface 0"}, "eth1": {"description": "not defined"}}
            },
            "sfo-dev2": {
                "interfaces": {
                    "eth0": {"description": "Interface 0"},
                    "eth1": {"description": "Interface 1"},
                    "eth2": {"description": "Interface 2"},
                }
            },
        },
    }


@pytest.fixture
def backend_b():
    """Provide an instance of BackendB subclass of DiffSync."""
    adapter = BackendB()
    adapter.load()
    return adapter


@pytest.fixture
def diff_children_nyc_dev1():
    """Fixture dict of DiffElement."""
    children = dict()
    device_name = "nyc-dev1"
    site_name = "nyc"
    for intf_name, intf in BackendB.DATA[site_name][device_name]["interfaces"].items():
        children[intf_name] = DiffElement(obj_type="interface", name=intf_name, keys=dict(device_name=device_name))
        children[intf_name].add_attrs(source=intf)

    for intf_name, intf in BackendA.DATA[site_name][device_name]["interfaces"].items():
        if intf_name not in children:
            children[intf_name] = DiffElement(obj_type="interface", name=intf_name, keys=dict(device_name=device_name))
        children[intf_name].add_attrs(dest=intf)

    return children


@pytest.fixture
def netbox_api_empty():
    """Provide an instance of NetBoxAPIAdapter with pynetbox initiliazed."""
    adapter = NetBoxAPIAdapter(nornir=None, settings={})
    adapter.netbox = pynetbox.api(url="http://mock", token="1234567890")

    return adapter


@pytest.fixture
def netbox_api_base():
    """Provide an instance of NetBoxAPIAdapter with pynetbox initiliazed."""
    adapter = NetBoxAPIAdapter(nornir=None, settings={})
    adapter.netbox = pynetbox.api(url="http://mock", token="1234567890")

    adapter.add(NetboxSite(name="HQ", remote_id=10))
    adapter.add(NetboxDevice(name="HQ-CORE-SW02", site_name="HQ", remote_id=29))
    adapter.add(NetboxInterface(name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02", remote_id=302))
    adapter.add(NetboxVlan(vid=111, site_name="HQ", remote_id=23))

    return adapter


@pytest.fixture
def network_importer_base():
    """Provide an instance of NetworkImporterAdapter with pynetbox initiliazed."""
    adapter = NetworkImporterAdapter(nornir=None, settings={})

    adapter.add(Site(name="HQ"))
    adapter.add(Device(name="HQ-CORE-SW02", site_name="HQ", remote_id=29))
    adapter.add(Interface(name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02"))
    adapter.add(Vlan(vid=111, site_name="HQ"))

    return adapter


@pytest.fixture
def empty_netbox_query():
    """Return an empty list to a list query."""
    value = {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }
    return value


@pytest.fixture
def nautobot_api_base():
    """Provide an instance of NautobotAPIAdapter with pynautoboot initiliazed."""
    adapter = NautobotAPIAdapter(nornir=None, settings={})
    adapter.nautobot = pynautobot.api(url="http://mock_nautobot", token="1234567890")

    adapter.add(NautobotSite(name="HQ", remote_id="a325e477-62fe-47f0-8b67-acf411b1868f"))
    adapter.add(NautobotDevice(name="HQ-CORE-SW02", site_name="HQ", remote_id="e0633a07-c3e2-41b0-a1df-4627392acf0a"))
    adapter.add(
        NautobotInterface(
            name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02", remote_id="fecc1d8f-99b1-491d-9bdf-1dcb394e27a1"
        )
    )
    adapter.add(NautobotVlan(vid=111, site_name="HQ", remote_id="464a2de3-fd5e-4b65-a58d-e0a2a617c12e"))

    return adapter


@pytest.fixture
def nautobot_api_empty():
    """Provide an instance of NautobotAPIAdapter with pynautobot initiliazed."""
    adapter = NautobotAPIAdapter(nornir=None, settings={})
    adapter.nautobot = pynautobot.api(url="http://mock", token="1234567890")

    return adapter


@pytest.fixture
def empty_nautobot_query():
    """Return an empty list to a list query."""
    value = {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }
    return value
