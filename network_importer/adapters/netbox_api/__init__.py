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
import logging
import warnings

import pynetbox

import network_importer.config as config  # pylint: disable=import-error
from network_importer.adapters.base import BaseAdapter  # pylint: disable=import-error
from network_importer.adapters.netbox_api.models import (  # pylint: disable=import-error
    NetboxSite,
    NetboxDevice,
    NetboxInterface,
    NetboxIPAddress,
    NetboxCable,
    NetboxPrefix,
    NetboxVlan,
)

from dsync.exceptions import ObjectAlreadyExist

warnings.filterwarnings("ignore", category=DeprecationWarning)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

LOGGER = logging.getLogger("network-importer")


class NetBoxAPIAdapter(BaseAdapter):

    site = NetboxSite
    device = NetboxDevice
    interface = NetboxInterface
    ip_address = NetboxIPAddress
    cable = NetboxCable
    vlan = NetboxVlan
    prefix = NetboxPrefix

    top_level = ["site", "device", "cable"]

    netbox = None
    source = "NetBox"

    def init(self):

        self.netbox = pynetbox.api(
            url=config.SETTINGS.netbox.address,
            token=config.SETTINGS.netbox.token,
            ssl_verify=config.SETTINGS.netbox.request_ssl_verify,
        )

        sites = {}
        device_names = []

        # Create all devices and site object from Nornir Inventory
        for hostname, host in self.nornir.inventory.hosts.items():
            if host.data["site"] not in sites.keys():
                site = self.site(name=host.data["site"], remote_id=host.data["site_id"])
                sites[host.data["site"]] = site
                self.add(site)
            else:
                site = sites[host.data["site"]]

            device = self.device(name=hostname, site_name=host.data["site"], remote_id=host.data["device_id"])
            self.add(device)

        # Import Prefix and Vlan per site
        for site in self.get_all(self.site):
            self.import_netbox_prefix(site)
            self.import_netbox_vlan(site)

        # Import interfaces and IP addresses for each devices
        devices = self.get_all(self.device)
        for device in devices:
            site = sites[device.site_name]
            device_names.append(device.name)
            self.import_netbox_device(site=site, device=device)

        # Import Cabling
        for site in self.get_all(self.site):
            self.import_netbox_cable(site=site, device_names=device_names)

    def import_netbox_device(self, site, device):
        """Import all interfaces and IP address from Netbox for a given device.

        Args:
            device (DSyncModel): Device to import
        """
        self.import_netbox_interface(site=site, device=device)
        self.import_netbox_ip_address(site=site, device=device)

    def import_netbox_prefix(self, site):
        """Import all prefixes from NetBox for a given site.

        Args:
            site (NetboxSite): Site to import prefix for
        """

        prefixes = self.netbox.ipam.prefixes.filter(site=site.name, status="active")

        for nb_prefix in prefixes:
            prefix_type = None

            prefix = self.prefix(
                prefix=nb_prefix.prefix, site_name=site.name, prefix_type=prefix_type, remote_id=nb_prefix.id,
            )

            self.add(prefix)
            site.add_child(prefix)

    def import_netbox_vlan(self, site):
        """Import all vlans from NetBox for a given site

        Args:
            site (NetboxSite): Site to import vlan for
        """
        vlans = self.netbox.ipam.vlans.filter(site=site.name)

        for nb_vlan in vlans:
            vlan = self.vlan(vid=nb_vlan.vid, site_name=site.name, name=nb_vlan.name, remote_id=nb_vlan.id,)
            self.add(vlan)
            site.add_child(vlan)

    def import_netbox_interface(self, site, device):
        """Import all interfaces & Ips from Netbox for a given device.

        Args:
            device (NetboxDevice): DSync object representing the device
        """

        # Import Interfaces
        intfs = self.netbox.dcim.interfaces.filter(device=device.name)
        for intf in intfs:

            interface = self.interface(
                name=intf.name,
                device_name=device.name,
                remote_id=intf.id,
                description=intf.description or None,
                mtu=intf.mtu,
            )

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

            if intf.tagged_vlans:
                for vid in [v.vid for v in intf.tagged_vlans]:
                    vlan, new = self.get_or_create_vlan(vlan=self.vlan(vid=vid, site_name=site.name), site=site)
                    interface.allowed_vlans.append(vlan.get_unique_id())

            if intf.untagged_vlan:
                vlan, new = self.get_or_create_vlan(
                    vlan=self.vlan(vid=intf.untagged_vlan.vid, site_name=site.name), site=site
                )
                interface.access_vlan = vlan.get_unique_id()

            new_intf, created = self.get_or_add(interface)
            if created:
                device.add_child(new_intf)

        LOGGER.debug("%s | Found %s interfaces for %s", self.source, len(intfs), device.name)

    def import_netbox_ip_address(self, site, device):  # pylint: disable=unused-argument

        ips = self.netbox.ipam.ip_addresses.filter(device=device.name)
        for ipaddr in ips:

            ip_address = self.ip_address(
                address=ipaddr.address,
                device_name=device.name,
                interface_name=ipaddr.interface.name,
                remote_id=ipaddr.id,
            )

            self.get_or_add(ip_address)
            interface = self.get(self.interface, keys=[device.name, ipaddr.interface.name])
            interface.add_child(ip_address)

        LOGGER.debug("%s | Found %s ip addresses for %s", self.source, len(ips), device.name)

    def import_netbox_cable(self, site, device_names):

        cables = self.netbox.dcim.cables.filter(site=site.name)

        nbr_cables = 0
        for nb_cable in cables:
            if nb_cable.termination_a_type != "dcim.interface" or nb_cable.termination_b_type != "dcim.interface":
                continue

            if nb_cable.termination_a.device.name not in device_names:
                LOGGER.debug(
                    "%s | Skipping cable %s because %s is not in the list of devices",
                    self.source,
                    nb_cable.id,
                    nb_cable.termination_a.device.name,
                )
                continue

            if nb_cable.termination_b.device.name not in device_names:
                LOGGER.debug(
                    "%s | Skipping cable %s because %s is not in the list of devices",
                    self.source,
                    nb_cable.id,
                    nb_cable.termination_b.device.name,
                )
                continue

            cable = self.cable(
                device_a_name=nb_cable.termination_a.device.name,
                interface_a_name=nb_cable.termination_a.name,
                device_z_name=nb_cable.termination_b.device.name,
                interface_z_name=nb_cable.termination_b.name,
                remote_id=nb_cable.id,
            )

            try:
                self.add(cable)

            except ObjectAlreadyExist:
                pass

            nbr_cables += 1

        LOGGER.debug("%s | Found %s cables in netbox for %s", self.source, nbr_cables, site.name)

    # -----------------------------------------------------
    # Interface
    # -----------------------------------------------------

    def interface_translate_params(self, keys, params):
        """Translate interface parameters into Netbox format

        Args:
            keys (dict): Dictionnary of primary keys of the object to translate
            params (dict): Dictionnary of attributes/parameters of the object to translate

        Returns:
            dict: Netbox parameters
        """

        def convert_vlan_to_nid(vlan_uid):
            vlan = self.get(self.vlan, keys=[vlan_uid])
            return vlan.remote_id

        nb_params = {}

        # Identify the id of the device this interface is attached to
        device = self.get(self.device, keys=[keys["device_name"]])
        nb_params["device"] = device.remote_id
        nb_params["name"] = keys["name"]

        if "is_lag" in params and params["is_lag"]:
            nb_params["type"] = "lag"
        elif "is_virtual" in params and params["is_virtual"]:
            nb_params["type"] = "virtual"
        else:
            nb_params["type"] = "other"

        if "mtu" in params:
            nb_params["mtu"] = params["mtu"]

        if "description" in params:
            nb_params["description"] = params["description"] or ""

        if "switchport_mode" in params and params["switchport_mode"] == "ACCESS":
            nb_params["mode"] = "access"
        elif "switchport_mode" in params and params["switchport_mode"] == "TRUNK":
            nb_params["switchport_mode"] = "tagged"

        # if is None:
        #     intf_properties["enabled"] = intf.active

        if config.SETTINGS.main.import_vlans != "no":
            if "mode" in params and params["mode"] in ["TRUNK", "ACCESS"] and params["access_vlan"]:
                nb_params["untagged_vlan"] = convert_vlan_to_nid(params["access_vlan"])
            elif "mode" in params and params["mode"] in ["TRUNK", "ACCESS"] and not params["access_vlan"]:
                nb_params["untagged_vlan"] = None

            if "mode" in params and params["mode"] in ["TRUNK", "L3_SUB_VLAN"] and params["allowed_vlans"]:
                nb_params["tagged_vlans"] = [convert_vlan_to_nid(vlan) for vlan in params["allowed_vlans"]]
            elif "mode" in params and params["mode"] in ["TRUNK", "L3_SUB_VLAN"] and not params["allowed_vlans"]:
                nb_params["tagged_vlans"] = []

        if "is_lag_member" in params and params["is_lag_member"]:
            # TODO add checks to ensure the parent interface is present and has a remote id
            parent_interface = self.get(self.interface, keys=[params["parent"]])
            nb_params["lag"] = parent_interface.remote_id

        elif "is_lag_member" in params and not params["is_lag_member"]:
            nb_params["lag"] = None

        return nb_params

    def create_interface(self, keys, params):
        """Create an interface object in Netbox.

        Args:
            keys (dict): Dictionnary of primary keys of the object to update
            params (dict): Dictionnary of attributes/parameters of the object to update

        Returns:
            NetboxInterface: DSync object newly created
        """

        nb_params = self.interface_translate_params(keys, params)

        intf = self.netbox.dcim.interfaces.create(**nb_params)
        LOGGER.debug("Created interface %s (%s) in NetBox", intf.name, intf.id)

        # Create the object in the local DB
        item = self.default_create(object_type="interface", keys=keys, params=params)
        item.remote_id = intf.id

        return item

    def update_interface(self, keys, params):
        """Update an interface object in Netbox.

        Args:
            keys (dict): Dictionnary of primary keys of the object to update
            params (dict): Dictionnary of attributes/parameters of the object to update

        Returns:
            NetboxInterface: DSync object
        """
        item = self.get(self.interface, keys=[keys["device_name"], keys["name"]])
        attrs = item.get_attrs()
        if attrs == params:
            return item

        nb_params = self.interface_translate_params(keys, params)

        intf = self.netbox.dcim.interfaces.get(item.remote_id)
        intf.update(data=nb_params)
        LOGGER.debug("Updated Interface %s %s (%s) in NetBox", item.device_name, item.name, item.remote_id)
        print(nb_params)

        for key, value in params.items():
            setattr(item, key, value)

        return item

    def delete_interface(self, keys, params):
        """Delete an interface object in Netbox.

        Args:
            keys (dict): Dictionnary of primary keys of the object to delete
            params (dict): Dictionnary of attributes/parameters of the object to delete

        Returns:
            NetboxInterface: DSync object
        """

        item = self.get(self.interface, keys=[keys["device_name"], keys["name"]])
        intf = self.netbox.dcim.interfaces.get(item.remote_id)
        intf.delete()

        item = self.default_delete(object_type="interface", keys=keys, params=params)

        return item

    # -----------------------------------------------------
    # IP Address
    # -----------------------------------------------------
    def create_ip_address(self, keys, params):

        interface = None
        if "interface_name" in params and "device_name" in params:
            interface = self.get(self.interface, keys=[params["device_name"], params["interface_name"]])

        if interface:
            ip_address = self.netbox.ipam.ip_addresses.create(address=keys["address"], interface=interface.remote_id)
        else:
            ip_address = self.netbox.ipam.ip_addresses.create(address=keys["address"])

        LOGGER.debug("Created IP %s (%s) in NetBox", ip_address.address, ip_address.id)

        item = self.default_create(object_type="ip_address", keys=keys, params=params)
        item.remote_id = ip_address.id

        return item

    def delete_ip_address(self, keys, params):

        item = self.get(self.ip_address, list(keys.values()))

        ipaddr = self.netbox.ipam.ip_addresses.get(item.remote_id)
        ipaddr.delete()

        item = self.default_delete(object_type="ip_address", keys=keys, params=params)

        return item

    # # -----------------------------------------------------
    # # Prefix
    # # -----------------------------------------------------
    def create_prefix(self, keys, params):

        site = self.get(self.site, keys=[keys["site_name"]])
        status = "active"

        prefix = self.netbox.ipam.prefixes.create(prefix=keys["prefix"], site=site.remote_id, status=status)
        LOGGER.debug("Created Prefix %s (%s) in NetBox", prefix.prefix, prefix.id)

        item = self.default_create(object_type="prefix", keys=keys, params=params)
        item.remote_id = prefix.id
        return item

    # def delete_prefix()
    # -----------------------------------------------------
    # Cable
    # -----------------------------------------------------
    def create_cable(self, keys, params):

        interface_a = self.get(self.interface, keys=[keys["device_a_name"], keys["interface_a_name"]])
        interface_z = self.get(self.interface, keys=[keys["device_z_name"], keys["interface_z_name"]])

        try:
            cable = self.netbox.dcim.cables.create(
                termination_a_type="dcim.interface",
                termination_b_type="dcim.interface",
                termination_a_id=interface_a.remote_id,
                termination_b_id=interface_z.remote_id,
            )
        except pynetbox.core.query.RequestError:
            LOGGER.warning("Unable to create Cable %s in %s", keys, self.source)
            return False

        item = self.default_create(object_type="cable", keys=keys, params=params)
        LOGGER.debug("Created Cable %s (%s) in NetBox", item.get_unique_id(), cable.id)

        item.remote_id = cable.id
        return item

    # -----------------------------------------------------
    # Vlans
    # -----------------------------------------------------
    def create_vlan(self, keys, params):

        site = self.get(self.site, keys=[keys["site_name"]])

        if "name" in params and params["name"]:
            vlan_name = params["name"]
        else:
            vlan_name = f"vlan-{keys['vid']}"

        try:
            vlan = self.netbox.ipam.vlans.create(vid=keys["vid"], name=vlan_name, site=site.remote_id)
        except pynetbox.core.query.RequestError:
            LOGGER.warning("Unable to create Vlan %s in %s", keys, self.source)
            return False

        item = self.default_create(object_type="vlan", keys=keys, params=params)
        item.remote_id = vlan.id

        return item
