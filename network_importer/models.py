"""DiffSync Models for the network importer.

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
from typing import List, Optional

from diffsync import DiffSyncModel


class Site(DiffSyncModel):
    """Site Model based on DiffSyncModel.

    A site must have a unique name and can be composed of Vlans and Prefixes.
    """

    _modelname = "site"
    _identifiers = ("name",)
    _children = {"vlan": "vlans", "prefix": "prefixes"}

    name: str
    prefixes: List = list()  # Correct as is, no need for Optional since it's initialized as an empty list
    vlans: List[str] = list()  # Same here


class Device(DiffSyncModel):
    """Device Model based on DiffSyncModel.

    A device must have a unique name and can be part of a site.
    """

    _modelname = "device"
    _identifiers = ("name",)
    _attributes = ("site_name",)
    _children = {"interface": "interfaces"}

    name: str
    site_name: Optional[str] = None
    interfaces: List = list()
    platform: Optional[str] = None
    model: Optional[str] = None
    role: Optional[str] = None
    vendor: Optional[str] = None


class Interface(DiffSyncModel):  # pylint: disable=too-many-instance-attributes
    """Interface Model based on DiffSyncModel.

    An interface must be attached to a device and the name must be unique per device.
    """

    _modelname = "interface"
    _identifiers = ("device_name", "name")
    _shortname = ("name",)
    _attributes = (
        "description",
        "is_virtual",
        "is_lag",
        "is_lag_member",
        "parent",
        "mode",
        "switchport_mode",
        "allowed_vlans",
        "access_vlan",
    )
    _children = {"ip_address": "ips"}

    name: str
    device_name: str

    description: Optional[str] = None
    mtu: Optional[int] = None
    speed: Optional[int] = None
    mode: Optional[str] = None  # TRUNK, ACCESS, L3, NONE
    switchport_mode: Optional[str] = "NONE"
    active: Optional[bool] = None
    is_virtual: Optional[bool] = None
    is_lag: Optional[bool] = None
    is_lag_member: Optional[bool] = None
    parent: Optional[str] = None

    lag_members: List[str] = list()
    allowed_vlans: List[str] = list()
    access_vlan: Optional[str] = None

    ips: List[str] = list()


class IPAddress(DiffSyncModel):
    """IPAddress Model based on DiffSyncModel.

    An IP address must be unique and can be associated with an interface.
    """

    _modelname = "ip_address"
    _identifiers = ("device_name", "interface_name", "address")

    device_name: str
    interface_name: str
    address: str


class Prefix(DiffSyncModel):
    """Prefix Model based on DiffSyncModel.

    A Prefix must be associated with a Site and must be unique within a site.
    """

    _modelname = "prefix"
    _identifiers = ("site_name", "prefix")
    _attributes = ("vlan",)

    prefix: str
    site_name: Optional[str] = None
    vlan: Optional[str] = None


class Cable(DiffSyncModel):
    """Cable Model based on DiffSyncModel."""

    _modelname = "cable"
    _identifiers = (
        "device_a_name",
        "interface_a_name",
        "device_z_name",
        "interface_z_name",
    )

    device_a_name: str
    interface_a_name: str
    device_z_name: str
    interface_z_name: str

    source: Optional[str] = None
    is_valid: bool = True
    error: Optional[str] = None

    def __init__(self, *args, **kwargs):
        """Ensure the cable is unique by ordering the devices alphabetically."""
        if "device_a_name" not in kwargs or "device_z_name" not in kwargs:
            raise ValueError("device_a_name and device_z_name are mandatory")
        if not kwargs["device_a_name"] or not kwargs["device_z_name"]:
            raise ValueError("device_a_name and device_z_name are mandatory and must not be None")

        keys_to_copy = ["device_a_name", "interface_a_name", "device_z_name", "interface_z_name"]
        ids = {key: kwargs[key] for key in keys_to_copy}

        devices = [kwargs["device_a_name"], kwargs["device_z_name"]]
        if sorted(devices) != devices:
            ids["device_a_name"] = kwargs["device_z_name"]
            ids["interface_a_name"] = kwargs["interface_z_name"]
            ids["device_z_name"] = kwargs["device_a_name"]
            ids["interface_z_name"] = kwargs["interface_a_name"]

        for key in keys_to_copy:
            del kwargs[key]

        super().__init__(*args, **ids, **kwargs)

    def get_device_intf(self, side):
        """Get the device name and the interface name for a given side.

        Args:
            side (str): site to query, must be either a or z

        Raises:
            ValueError: when the side is not either a or z

        Returns:
            (device_name (str), interface_name (str))
        """
        if side.lower() == "a":
            return self.device_a_name, self.interface_a_name

        if side.lower() == "z":
            return self.device_z_name, self.interface_z_name

        raise ValueError("side must be either 'a' or 'z'")


class Vlan(DiffSyncModel):
    """Vlan Model based on DiffSyncModel.

    An Vlan must be associated with a Site and the vlan_id msut be unique within a site.
    """

    _modelname = "vlan"
    _identifiers = ("site_name", "vid")
    _attributes = ("name", "associated_devices")

    vid: int
    site_name: str
    name: Optional[str] = None

    associated_devices: List[str] = list()

    def add_device(self, device_name):
        """Add a device to the list of associated devices.

        Args:
            device_name (str): name of a device to associate with this VLAN
        """
        if device_name not in self.associated_devices:
            self.associated_devices.append(device_name)
            self.associated_devices = sorted(self.associated_devices)
