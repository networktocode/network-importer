"""NautobotAPIAdapter class."""
import logging
import warnings

import pynautobot
from diffsync.exceptions import ObjectAlreadyExists, ObjectNotFound
from packaging.version import Version, InvalidVersion
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import network_importer.config as config  # pylint: disable=import-error
from network_importer.adapters.base import BaseAdapter  # pylint: disable=import-error
from network_importer.adapters.nautobot_api.models import (  # pylint: disable=import-error
    NautobotSite,
    NautobotDevice,
    NautobotInterface,
    NautobotIPAddress,
    NautobotCable,
    NautobotPrefix,
    NautobotVlan,
)
from network_importer.adapters.nautobot_api.settings import InventorySettings, AdapterSettings
from network_importer.adapters.nautobot_api.tasks import query_device_info_from_nautobot

warnings.filterwarnings("ignore", category=DeprecationWarning)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

LOGGER = logging.getLogger("network-importer")


class NautobotAPIAdapter(BaseAdapter):
    """Adapter to import Data from a Nautobot Server over its API."""

    site = NautobotSite
    device = NautobotDevice
    interface = NautobotInterface
    ip_address = NautobotIPAddress
    cable = NautobotCable
    vlan = NautobotVlan
    prefix = NautobotPrefix

    top_level = ["site", "device", "cable"]

    nautobot = None
    nautobot_version = None

    settings_class = AdapterSettings

    type = "Nautobot"

    query_device_info_from_nautobot = query_device_info_from_nautobot

    def _is_tag_present(self, nautobot_obj):
        """Find if tag is present for a given object."""
        if isinstance(nautobot_obj, dict) and not nautobot_obj.get("tags", None):  # pylint: disable=no-else-return
            return False
        elif not isinstance(nautobot_obj, dict):  # pylint: disable=no-else-return
            try:
                nautobot_obj["tags"]
            except AttributeError:
                return False
        elif not nautobot_obj["tags"]:
            return False

        for tag in self.settings.model_flag_tags:
            if tag in nautobot_obj["tags"]:
                LOGGER.debug(
                    "Tag (%s) found for object %s. Marked for diffsync flag assignment.",
                    tag,
                    nautobot_obj,
                )
                return True
        return False

    def apply_model_flag(self, diffsync_obj, nautobot_obj):
        """Helper function for DiffSync Flag assignment."""
        model_flag = self.settings.model_flag

        if model_flag and self._is_tag_present(nautobot_obj):
            LOGGER.info(
                "DiffSync model flag (%s) applied to object %s",
                model_flag,
                nautobot_obj,
            )
            diffsync_obj.model_flags = model_flag
        return diffsync_obj

    def _check_nautobot_version(self):
        """Check the version of Nautobot defined in the configuration and load the proper models as needed.

        The default models should work with the latest version of Nautobot
        Version specific models should be used to manage older version.
        """
        try:
            self.nautobot_version = Version(self.nautobot.version)
        except InvalidVersion:
            LOGGER.warning(
                "Unable to identify the current version of Nautobot from Pynautobot, using the default version."
            )
            return

    def load(self):
        """Initialize pynautobot and load all data from nautobot in the local cache."""
        inventory_settings = InventorySettings(**config.SETTINGS.inventory.settings)
        self.nautobot = pynautobot.api(url=inventory_settings.address, token=inventory_settings.token)
        if not inventory_settings.verify_ssl:
            self.nautobot.http_session.verify = False
        else:
            self.nautobot.http_session.verify = True

        if inventory_settings.http_retries:
            retries = Retry(total=inventory_settings.http_retries,
                            backoff_factor=0.5,
                            status_forcelist=[429, 500, 502, 503, 504, ],
                            allowed_methods=False
                            )
            self.nautobot.http_session.mount(self.nautobot.base_url, HTTPAdapter(max_retries=retries))

        self._check_nautobot_version()

        sites = {}
        device_names = []

        results = self.nornir.run(task=query_device_info_from_nautobot)

        for device_name, items in results.items():
            if items[0].failed:
                continue

            result = items[0].result
            nb_device = result["device"]
            site_name = nb_device["site"].get("slug")

            if site_name not in sites:
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
            self.load_nautobot_prefix(site)
            self.load_nautobot_vlan(site)

        # Load interfaces and IP addresses for each devices
        devices = self.get_all(self.device)
        for device in devices:
            site = sites[device.site_name]
            device_names.append(device.name)
            self.load_nautobot_device(site=site, device=device)

        # Load Cabling
        for site in self.get_all(self.site):
            self.load_nautobot_cable(site=site, device_names=device_names)

    def load_nautobot_device(self, site, device):
        """Import all interfaces and IP address from Nautobot for a given device.

        Args:
            site (NautobotSite): Site the device is part of
            device (DiffSyncModel): Device to import
        """
        self.load_nautobot_interface(site=site, device=device)
        self.load_nautobot_ip_address(site=site, device=device)

    def load_nautobot_prefix(self, site):
        """Import all prefixes from Nautobot for a given site.

        Args:
            site (NautobotSite): Site to import prefix for
        """
        if not config.SETTINGS.main.import_prefixes:
            return

        prefixes = self.nautobot.ipam.prefixes.filter(site=site.name, status="active")

        for nb_prefix in prefixes:
            prefix = self.prefix(
                prefix=nb_prefix.prefix,
                site_name=site.name,
                remote_id=nb_prefix.id,
            )
            prefix = self.apply_model_flag(prefix, nb_prefix)

            if nb_prefix.vlan:
                prefix.vlan = self.vlan.create_unique_id(vid=nb_prefix.vlan.vid, site_name=site.name)

            self.add(prefix)
            site.add_child(prefix)

    def load_nautobot_vlan(self, site):
        """Import all vlans from Nautobot for a given site.

        Args:
            site (NautobotSite): Site to import vlan for
        """
        if config.SETTINGS.main.import_vlans in [False, "no"]:
            return

        vlans = self.nautobot.ipam.vlans.filter(site=site.name)

        for nb_vlan in vlans:
            vlan = self.vlan.create_from_pynautobot(diffsync=self, obj=nb_vlan, site_name=site.name)
            self.add(vlan)
            site.add_child(vlan)

    def convert_interface_from_nautobot(
        self, device, intf, site=None
    ):  # pylint: disable=too-many-branches,too-many-statements
        """Convert PyNautobot interface object to NautobotInterface model.

        Args:
            site (NautobotSite): [description]
            device (NautobotDevice): [description]
            intf (pynautobot interface object): [description]
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

    def load_nautobot_interface(self, site, device):
        """Import all interfaces & Ips from Nautobot for a given device.

        Args:
            site (NautobotSite): DiffSync object representing a site
            device (NautobotDevice): DiffSync object representing the device
        """
        intfs = self.nautobot.dcim.interfaces.filter(device=device.name)
        for intf in intfs:
            self.convert_interface_from_nautobot(site=site, device=device, intf=intf)

        LOGGER.debug("%s | Found %s interfaces for %s", self.name, len(intfs), device.name)

    def load_nautobot_ip_address(self, site, device):  # pylint: disable=unused-argument
        """Import all IP addresses from Nautobot for a given device.

        Args:
            site (NautobotSite): DiffSync object representing a site
            device (NautobotDevice): DiffSync object representing the device
        """
        if not config.SETTINGS.main.import_ips:
            return

        ips = self.nautobot.ipam.ip_addresses.filter(device=device.name)
        for ipaddr in ips:
            ip_address = self.ip_address.create_from_pynautobot(diffsync=self, obj=ipaddr, device_name=device.name)
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

    def load_nautobot_cable(self, site, device_names):
        """Import all Cables from Nautobot for a given site.

        If both devices at each end of the cables are not in the list of device_names, the cable will be ignored.

        Args:
            site (Site): Site object to import cables for
            device_names (list): List of device names that are part of the inventory
        """
        cables = self.nautobot.dcim.cables.filter(site=site.name)

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
                status="connected",
            )

            try:
                self.add(cable)
            except ObjectAlreadyExists:
                pass

            nbr_cables += 1

        LOGGER.debug("%s | Found %s cables in nautobot for %s", self.name, nbr_cables, site.name)

    def get_intf_from_nautobot(self, device_name, intf_name):
        """Get an interface from Nautobot based on the name of the device and the name of the interface.

        Exactly one return must be returned from Nautobot, the function will return False if more than 1 result are returned.

        Args:
            device_name (str): name of the device in nautobot
            intf_name (str): name of the interface in Nautobot

        Returns:
            NautobotInterface, bool: Interface in DiffSync format
        """
        intfs = self.nautobot.dcim.interfaces.filter(name=intf_name, device=device_name)

        if len(intfs) == 0:
            # LOGGER.debug("Unable to find the interface in Nautobot for %s %s, nothing returned", device_name, intf_name)
            return False

        if len(intfs) > 1:
            LOGGER.warning(
                "Unable to find the proper interface in Nautobot for %s %s, more than 1 element returned",
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
