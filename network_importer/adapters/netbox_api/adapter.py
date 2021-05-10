"""NetBoxAPIAdapter class."""
import logging
import warnings

import requests
import pynetbox
from packaging.version import Version, InvalidVersion

from diffsync.exceptions import ObjectAlreadyExists, ObjectNotFound
import network_importer.config as config  # pylint: disable=import-error
from network_importer.adapters.base import BaseAdapter  # pylint: disable=import-error
from network_importer.adapters.netbox_api.models import (  # pylint: disable=import-error
    NetboxSite,
    NetboxDevice,
    NetboxInterface,
    NetboxIPAddress,
    NetboxIPAddressPre29,
    NetboxCable,
    NetboxPrefix,
    NetboxVlan,
    NetboxVlanPre29,
)
from network_importer.adapters.netbox_api.tasks import query_device_info_from_netbox
from network_importer.adapters.netbox_api.settings import InventorySettings, AdapterSettings

warnings.filterwarnings("ignore", category=DeprecationWarning)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

LOGGER = logging.getLogger("network-importer")


class NetBoxAPIAdapter(BaseAdapter):
    """Adapter to import Data from a Netbox Server over its API."""

    site = NetboxSite
    device = NetboxDevice
    interface = NetboxInterface
    ip_address = NetboxIPAddress
    cable = NetboxCable
    vlan = NetboxVlan
    prefix = NetboxPrefix

    top_level = ["site", "device", "cable"]

    netbox = None
    netbox_version = None

    settings_class = AdapterSettings

    type = "Netbox"

    query_device_info_from_netbox = query_device_info_from_netbox

    def _is_tag_present(self, netbox_obj):
        """Find if tag is present for a given object."""
        if isinstance(netbox_obj, dict) and not netbox_obj.get("tags", None):  # pylint: disable=no-else-return
            return False
        elif not isinstance(netbox_obj, dict):  # pylint: disable=no-else-return
            try:
                netbox_obj["tags"]
            except AttributeError:
                return False
        elif not netbox_obj["tags"]:
            return False

        for tag in self.settings.model_flag_tags:
            if tag in netbox_obj["tags"]:
                LOGGER.debug(
                    "Tag (%s) found for object %s. Marked for diffsync flag assignment.", tag, netbox_obj,
                )
                return True
        return False

    def apply_model_flag(self, diffsync_obj, netbox_obj):
        """Helper function for DiffSync Flag assignment."""
        model_flag = self.settings.model_flag

        if model_flag and self._is_tag_present(netbox_obj):
            LOGGER.info(
                "DiffSync model flag (%s) applied to object %s", model_flag, netbox_obj,
            )
            diffsync_obj.model_flags = model_flag
        return diffsync_obj

    def _check_netbox_version(self):
        """Check the version of Netbox defined in the configuration and load the proper models as needed.

        The default models should work with the latest version of Netbox
        Version specific models should be used to manage older version.
        """
        try:
            self.netbox_version = Version(self.netbox.version)
        except InvalidVersion:
            LOGGER.warning("Unable to identify the current version of Netbox from Pynetbox, using the default version.")
            return

        if self.netbox_version < Version("2.9"):
            LOGGER.debug("Version %s of netbox detected, will update the ip_address model.", self.netbox_version)
            self.ip_address = NetboxIPAddressPre29
            self.vlan = NetboxVlanPre29

    def load(self):
        """Initialize pynetbox and load all data from netbox in the local cache."""
        inventory_settings = InventorySettings(**config.SETTINGS.inventory.settings)
        self.netbox = pynetbox.api(url=inventory_settings.address, token=inventory_settings.token)

        if not inventory_settings.verify_ssl:
            session = requests.Session()
            session.verify = False
            self.netbox.http_session = session

        self._check_netbox_version()

        sites = {}
        device_names = []

        results = self.nornir.run(task=query_device_info_from_netbox)

        for device_name, items in results.items():
            if items[0].failed:
                continue

            result = items[0].result
            nb_device = result["device"]
            site_name = nb_device["site"].get("slug")

            if site_name not in sites.keys():
                site = self.site(name=site_name, remote_id=nb_device["site"].get("id"))
                sites[site_name] = site
                self.add(site)
            else:
                site = sites[site_name]

            device = self.device(name=device_name, site_name=site_name, remote_id=nb_device["id"])

            if nb_device["primary_ip"]:
                device.primary_ip = nb_device["primary_ip"].get("address")

            device = self.apply_model_flag(device, nb_device)
            self.add(device)

        # Load Prefix and Vlan per site
        for site in self.get_all(self.site):
            self.load_netbox_prefix(site)
            self.load_netbox_vlan(site)

        # Load interfaces and IP addresses for each devices
        devices = self.get_all(self.device)
        for device in devices:
            site = sites[device.site_name]
            device_names.append(device.name)
            self.load_netbox_device(site=site, device=device)

        # Load Cabling
        for site in self.get_all(self.site):
            self.load_netbox_cable(site=site, device_names=device_names)

    def load_netbox_device(self, site, device):
        """Import all interfaces and IP address from Netbox for a given device.

        Args:
            site (NetboxSite): Site the device is part of
            device (DiffSyncModel): Device to import
        """
        self.load_netbox_interface(site=site, device=device)
        self.load_netbox_ip_address(site=site, device=device)

    def load_netbox_prefix(self, site):
        """Import all prefixes from NetBox for a given site.

        Args:
            site (NetboxSite): Site to import prefix for
        """
        if not config.SETTINGS.main.import_prefixes:
            return

        prefixes = self.netbox.ipam.prefixes.filter(site=site.name, status="active")

        for nb_prefix in prefixes:

            prefix = self.prefix(prefix=nb_prefix.prefix, site_name=site.name, remote_id=nb_prefix.id,)
            prefix = self.apply_model_flag(prefix, nb_prefix)

            if nb_prefix.vlan:
                prefix.vlan = self.vlan.create_unique_id(vid=nb_prefix.vlan.vid, site_name=site.name)

            self.add(prefix)
            site.add_child(prefix)

    def load_netbox_vlan(self, site):
        """Import all vlans from NetBox for a given site.

        Args:
            site (NetboxSite): Site to import vlan for
        """
        if config.SETTINGS.main.import_vlans in [False, "no"]:
            return

        vlans = self.netbox.ipam.vlans.filter(site=site.name)

        for nb_vlan in vlans:
            vlan = self.vlan.create_from_pynetbox(diffsync=self, obj=nb_vlan, site_name=site.name)
            self.add(vlan)
            site.add_child(vlan)

    def convert_interface_from_netbox(
        self, device, intf, site=None
    ):  # pylint: disable=too-many-branches,too-many-statements
        """Convert PyNetBox interface object to NetBoxInterface model.

        Args:
            site (NetBoxSite): [description]
            device (NetBoxDevice): [description]
            intf (pynetbox interface object): [description]
        """
        interface = self.interface(
            name=intf.name,
            device_name=device.name,
            remote_id=intf.id,
            description=intf.description or None,
            mtu=intf.mtu,
        )

        import_vlans = False
        if config.SETTINGS.main.import_vlans not in [False, "no"]:
            import_vlans = True

        # Define status if it's enabled in the config file
        if config.SETTINGS.main.import_intf_status:
            interface.active = intf.enabled

        # Identify if the interface is physical or virtual and if it's part of a Lag
        if intf.type and intf.type.value == "lag":
            interface.is_lag = True
            interface.is_virtual = False
        elif intf.type and intf.type.value == "virtual":
            interface.is_virtual = True
            interface.is_lag = False
        else:
            interface.is_lag = False
            interface.is_virtual = False

        if intf.lag:
            interface.is_lag_member = True
            interface.is_lag = False
            interface.is_virtual = False
            parent_interface_uid = self.interface(name=intf.lag.name, device_name=device.name).get_unique_id()
            interface.parent = parent_interface_uid

        # identify Interface Mode
        if intf.mode and intf.mode.value == "access":
            interface.switchport_mode = "ACCESS"
            interface.mode = interface.switchport_mode
        elif intf.mode and intf.mode.value == "tagged":
            interface.switchport_mode = "TRUNK"
            interface.mode = interface.switchport_mode
        elif not intf.mode and intf.tagged_vlans:
            interface.switchport_mode = "NONE"
            interface.mode = "L3_SUB_VLAN"
        else:
            interface.switchport_mode = "NONE"
            interface.mode = "NONE"

        # Identify Interface Speed based on the type
        if intf.type and intf.type.value == 800:
            interface.speed = 1000000000
        elif intf.type and intf.type.value == 1100:
            interface.speed = 1000000000
        elif intf.type and intf.type.value == 1200:
            interface.speed = 10000000000
        elif intf.type and intf.type.value == 1350:
            interface.speed = 25000000000
        elif intf.type and intf.type.value == 1400:
            interface.speed = 40000000000
        elif intf.type and intf.type.value == 1600:
            interface.speed = 100000000000

        if site and intf.tagged_vlans and import_vlans:
            for vid in [v.vid for v in intf.tagged_vlans]:
                try:
                    vlan = self.get(self.vlan, identifier=dict(vid=vid, site_name=site.name))
                    interface.allowed_vlans.append(vlan.get_unique_id())
                except ObjectNotFound:
                    LOGGER.debug("%s | VLAN %s is not present for site %s", self.name, vid, site.name)

        if site and intf.untagged_vlan and import_vlans:
            try:
                vlan = self.get(self.vlan, identifier=dict(vid=intf.untagged_vlan.vid, site_name=site.name))
                interface.access_vlan = vlan.get_unique_id()
            except ObjectNotFound:
                LOGGER.debug("%s | VLAN %s is not present for site %s", self.name, intf.untagged_vlan.vid, site.name)

        if intf.connected_endpoint_type:
            interface.connected_endpoint_type = intf.connected_endpoint_type

        new_intf, created = self.get_or_add(interface)
        if created:
            device.add_child(new_intf)

        return new_intf

    def load_netbox_interface(self, site, device):
        """Import all interfaces & Ips from Netbox for a given device.

        Args:
            site (NetboxSite): DiffSync object representing a site
            device (NetboxDevice): DiffSync object representing the device
        """
        intfs = self.netbox.dcim.interfaces.filter(device=device.name)
        for intf in intfs:
            self.convert_interface_from_netbox(site=site, device=device, intf=intf)

        LOGGER.debug("%s | Found %s interfaces for %s", self.name, len(intfs), device.name)

    def load_netbox_ip_address(self, site, device):  # pylint: disable=unused-argument
        """Import all IP addresses from NetBox for a given device.

        Args:
            site (NetboxSite): DiffSync object representing a site
            device (NetboxDevice): DiffSync object representing the device
        """
        if not config.SETTINGS.main.import_ips:
            return

        ips = self.netbox.ipam.ip_addresses.filter(device=device.name)
        for ipaddr in ips:
            ip_address = self.ip_address.create_from_pynetbox(diffsync=self, obj=ipaddr, device_name=device.name)
            ip_address, _ = self.get_or_add(ip_address)

            interface = self.get(
                self.interface, identifier=dict(device_name=device.name, name=ip_address.interface_name)
            )
            try:
                interface.add_child(ip_address)
            except ObjectAlreadyExists:
                LOGGER.error(
                    "%s | Duplicate IP found for %s (%s) ; IP already imported.", self.name, ip_address, device.name
                )

        LOGGER.debug("%s | Found %s ip addresses for %s", self.name, len(ips), device.name)

    def load_netbox_cable(self, site, device_names):
        """Import all Cables from NetBox for a given site.

        If both devices at each end of the cables are not in the list of device_names, the cable will be ignored.

        Args:
            site (Site): Site object to import cables for
            device_names (list): List of device names that are part of the inventory
        """
        cables = self.netbox.dcim.cables.filter(site=site.name)

        nbr_cables = 0
        for nb_cable in cables:
            if nb_cable.termination_a_type != "dcim.interface" or nb_cable.termination_b_type != "dcim.interface":
                continue

            if (nb_cable.termination_a.device.name not in device_names) and (
                nb_cable.termination_b.device.name not in device_names
            ):
                LOGGER.debug(
                    "%s | Skipping cable %s because neither devices (%s, %s) is in the list of devices",
                    self.name,
                    nb_cable.id,
                    nb_cable.termination_a.device.name,
                    nb_cable.termination_b.device.name,
                )
                continue

            # Disabling this check for now until we are able to allow user to control how cabling should be imported
            # if nb_cable.termination_a.device.name not in device_names:
            #     LOGGER.debug(
            #         "%s | Skipping cable %s because %s is not in the list of devices",
            #         self.name,
            #         nb_cable.id,
            #         nb_cable.termination_a.device.name,
            #     )
            #     continue

            # if nb_cable.termination_b.device.name not in device_names:
            #     LOGGER.debug(
            #         "%s | Skipping cable %s because %s is not in the list of devices",
            #         self.name,
            #         nb_cable.id,
            #         nb_cable.termination_b.device.name,
            #     )
            #     continue

            cable = self.cable(
                device_a_name=nb_cable.termination_a.device.name,
                interface_a_name=nb_cable.termination_a.name,
                device_z_name=nb_cable.termination_b.device.name,
                interface_z_name=nb_cable.termination_b.name,
                remote_id=nb_cable.id,
            )

            try:
                self.add(cable)
            except ObjectAlreadyExists:
                pass

            nbr_cables += 1

        LOGGER.debug("%s | Found %s cables in netbox for %s", self.name, nbr_cables, site.name)

    def get_intf_from_netbox(self, device_name, intf_name):
        """Get an interface from NetBox based on the name of the device and the name of the interface.

        Exactly one return must be returned from NetBox, the function will return False if more than 1 result are returned.

        Args:
            device_name (str): name of the device in netbox
            intf_name (str): name of the interface in Netbox

        Returns:
            NetBoxInterface, bool: Interface in DiffSync format
        """
        intfs = self.netbox.dcim.interfaces.filter(name=intf_name, device=device_name)

        if len(intfs) == 0:
            # LOGGER.debug("Unable to find the interface in NetBox for %s %s, nothing returned", device_name, intf_name)
            return False

        if len(intfs) > 1:
            LOGGER.warning(
                "Unable to find the proper interface in NetBox for %s %s, more than 1 element returned",
                device_name,
                intf_name,
            )
            return False

        intf = self.interface(name=intf_name, device_name=device_name, remote_id=intfs[0].id)
        intf = self.apply_model_flag(intf, intfs[0])

        if intfs[0].connected_endpoint_type:
            intf.connected_endpoint_type = intfs[0].connected_endpoint_type

        self.add(intf)

        return intf
