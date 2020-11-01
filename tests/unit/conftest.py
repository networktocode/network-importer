"""Used to setup fixtures to be used through tests"""
import pytest

import pynetbox
from diffsync import DiffSync
from diffsync.diff import DiffElement

# from diffsync.exceptions import ObjectNotCreated, ObjectNotUpdated, ObjectNotDeleted

from network_importer.models import Site, Device, Interface, Vlan

from network_importer.adapters.network_importer.adapter import NetworkImporterAdapter

from network_importer.adapters.netbox_api.adapter import NetBoxAPIAdapter
from network_importer.adapters.netbox_api.models import NetboxSite, NetboxDevice, NetboxInterface, NetboxVlan


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


class GenericBackend(DiffSync):
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
    diffsync = BackendA()
    diffsync.load()
    return diffsync


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
    diffsync = BackendB()
    diffsync.load()
    return diffsync


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
    diffsync = NetBoxAPIAdapter(nornir=None)
    diffsync.netbox = pynetbox.api(url="http://mock", token="1234567890")

    return diffsync


@pytest.fixture
def netbox_api_base():
    """Provide an instance of NetBoxAPIAdapter with pynetbox initiliazed."""
    diffsync = NetBoxAPIAdapter(nornir=None)
    diffsync.netbox = pynetbox.api(url="http://mock", token="1234567890")

    diffsync.add(NetboxSite(name="HQ", remote_id=10))
    diffsync.add(NetboxDevice(name="HQ-CORE-SW02", site_name="HQ", remote_id=29))
    diffsync.add(NetboxInterface(name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02", remote_id=302))
    diffsync.add(NetboxVlan(vid=111, site_name="HQ", remote_id=23))

    return diffsync


@pytest.fixture
def network_importer_base():
    """Provide an instance of NetworkImporterAdapter with pynetbox initiliazed."""
    diffsync = NetworkImporterAdapter(nornir=None)

    diffsync.add(Site(name="HQ"))
    diffsync.add(Device(name="HQ-CORE-SW02", site_name="HQ", remote_id=29))
    diffsync.add(Interface(name="TenGigabitEthernet1/0/1", device_name="HQ-CORE-SW02"))
    diffsync.add(Vlan(vid=111, site_name="HQ"))

    return diffsync
