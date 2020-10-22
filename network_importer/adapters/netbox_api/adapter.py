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
from network_importer.adapters.netbox_api.tasks import query_device_info_from_netbox

from dsync.exceptions import ObjectAlreadyExists

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

    type = "Netbox"

    query_device_info_from_netbox = query_device_info_from_netbox

    def load(self):

        self.netbox = pynetbox.api(
            url=config.SETTINGS.netbox.address,
            token=config.SETTINGS.netbox.token,
            ssl_verify=config.SETTINGS.netbox.request_ssl_verify,
        )

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
            device (DSyncModel): Device to import
        """
        self.load_netbox_interface(site=site, device=device)
        self.load_netbox_ip_address(site=site, device=device)

    def load_netbox_prefix(self, site):
        """Import all prefixes from NetBox for a given site.

        Args:
            site (NetboxSite): Site to import prefix for
        """
        if not config.SETTINGS.main.import_prefixes:
            return False

        prefixes = self.netbox.ipam.prefixes.filter(site=site.name, status="active")

        for nb_prefix in prefixes:

            prefix = self.prefix(prefix=nb_prefix.prefix, site_name=site.name, remote_id=nb_prefix.id,)

            if nb_prefix.vlan:
                prefix.vlan = self.vlan.create_unique_id(vid=nb_prefix.vlan.vid, site_name=site.name)

            self.add(prefix)
            site.add_child(prefix)

    def load_netbox_vlan(self, site):
        """Import all vlans from NetBox for a given site

        Args:
            site (NetboxSite): Site to import vlan for
        """
        if config.SETTINGS.main.import_vlans in [False, "no"]:
            return False

        vlans = self.netbox.ipam.vlans.filter(site=site.name)

        for nb_vlan in vlans:
            vlan = self.vlan(vid=nb_vlan.vid, site_name=site.name, name=nb_vlan.name, remote_id=nb_vlan.id,)
            self.add(vlan)
            site.add_child(vlan)

    def convert_interface_from_netbox(self, device, intf, site=None):
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

        if site and intf.tagged_vlans:
            for vid in [v.vid for v in intf.tagged_vlans]:
                vlan, new = self.get_or_create_vlan(vlan=self.vlan(vid=vid, site_name=site.name), site=site)
                interface.allowed_vlans.append(vlan.get_unique_id())

        if site and intf.untagged_vlan:
            vlan, new = self.get_or_create_vlan(
                vlan=self.vlan(vid=intf.untagged_vlan.vid, site_name=site.name), site=site
            )
            interface.access_vlan = vlan.get_unique_id()

        if intf.connected_endpoint_type:
            interface.connected_endpoint_type = intf.connected_endpoint_type

        new_intf, created = self.get_or_add(interface)
        if created:
            device.add_child(new_intf)

        return new_intf

    def load_netbox_interface(self, site, device):
        """Import all interfaces & Ips from Netbox for a given device.

        Args:
            site (NetboxSite): DSync object representing a site
            device (NetboxDevice): DSync object representing the device
        """

        intfs = self.netbox.dcim.interfaces.filter(device=device.name)
        for intf in intfs:
            self.convert_interface_from_netbox(site=site, device=device, intf=intf)

        LOGGER.debug("%s | Found %s interfaces for %s", self.name, len(intfs), device.name)

    def load_netbox_ip_address(self, site, device):  # pylint: disable=unused-argument
        """Import all IP addresses from NetBox for a given device

        Args:
            site (NetboxSite): DSync object representing a site
            device (NetboxDevice): DSync object representing the device
        """
        if not config.SETTINGS.main.import_ips:
            return

        ips = self.netbox.ipam.ip_addresses.filter(device=device.name)
        for ipaddr in ips:

            ip_address = self.ip_address(
                address=ipaddr.address,
                device_name=device.name,
                interface_name=ipaddr.interface.name,
                remote_id=ipaddr.id,
            )

            self.get_or_add(ip_address)
            interface = self.get(self.interface, identifier=dict(device_name=device.name, name=ipaddr.interface.name))
            interface.add_child(ip_address)

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

<<<<<<< HEAD
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
            if vlan:
                return vlan.remote_id
            return None

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

        if config.SETTINGS.main.import_vlans not in [False, "no"]:
            if "mode" in params and params["mode"] in ["TRUNK", "ACCESS"] and params["access_vlan"]:
                nb_params["untagged_vlan"] = convert_vlan_to_nid(params["access_vlan"])
            elif "mode" in params and params["mode"] in ["TRUNK", "ACCESS"] and not params["access_vlan"]:
                nb_params["untagged_vlan"] = None

            if "mode" in params and params["mode"] in ["TRUNK", "L3_SUB_VLAN"] and params["allowed_vlans"]:
                nb_params["tagged_vlans"] = [convert_vlan_to_nid(vlan) for vlan in params["allowed_vlans"]]
            elif "mode" in params and params["mode"] in ["TRUNK", "L3_SUB_VLAN"] and not params["allowed_vlans"]:
                nb_params["tagged_vlans"] = []

        if "is_lag_member" in params and params["is_lag_member"]:
            parent_interface = self.get(self.interface, keys=[params["parent"]])
            if parent_interface and parent_interface.remote_id:
                nb_params["lag"] = parent_interface.remote_id
            else:
                # TODO Can we maybe create the parent interface at this point?
                LOGGER.warning("Parent interface %s of %s does not exist.", params["parent"], keys["name"])

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
        LOGGER.info("Updated Interface %s %s (%s) in NetBox", item.device_name, item.name, item.remote_id)
        # print(nb_params)

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

        # Check if the interface has some Ips, check if it is the management interface
        if item.ips:
            dev = self.get(self.device, keys=[item.device_name])
            if dev.primary_ip and dev.primary_ip in item.ips:
                LOGGER.warning(
                    "Unable to delete interface %s on %s, because it's currently the management interface",
                    item.name,
                    dev.name,
                )
                return item

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
        """Delete an IP address in NetBox

        Args:
            keys (dict): Dictionnary of primary keys of the object to delete
            params (dict): Dictionnary of attributes/parameters of the object to delete

        Returns:
            NetboxInterface: DSync object
        """
        item = self.get(self.ip_address, list(keys.values()))

        ipaddr = self.netbox.ipam.ip_addresses.get(item.remote_id)
        ipaddr.delete()

        item = self.default_delete(object_type="ip_address", keys=keys, params=params)

        return item

    # # -----------------------------------------------------
    # # Prefix
    # # -----------------------------------------------------
    def create_prefix(self, keys, params):
        """Create a Prefix in NetBox

        Args:
            keys (dict): Dictionnary of primary keys of the prefix to create
            params (dict): Dictionnary of attributes/parameters of the prefix to create

        Returns:
            NetboxPrefix: DSync object
        """
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
        """Create a Cable in NetBox

        Args:
            keys (dict): Dictionnary of primary keys of the object to delete
            params (dict): Dictionnary of attributes/parameters of the object to delete

        Returns:
            NetboxInterface: DSync object
        """
        interface_a = self.get(self.interface, keys=[keys["device_a_name"], keys["interface_a_name"]])
        interface_z = self.get(self.interface, keys=[keys["device_z_name"], keys["interface_z_name"]])

        if not interface_a:
            interface_a = self._get_intf_from_netbox(
                device_name=keys["device_a_name"], intf_name=keys["interface_a_name"]
            )

        elif not interface_z:
            interface_z = self._get_intf_from_netbox(
                device_name=keys["device_z_name"], intf_name=keys["interface_z_name"]
            )

        if not interface_a or not interface_z:
            return False

        if interface_a.connected_endpoint_type:
            LOGGER.info(
                "Unable to create Cable in %s, port %s %s is already connected",
                self.source,
                keys["device_a_name"],
                keys["interface_a_name"],
            )
            return False

        if interface_z.connected_endpoint_type:
            LOGGER.info(
                "Unable to create Cable in %s, port %s %s is already connected",
                self.source,
                keys["device_z_name"],
                keys["interface_z_name"],
            )
            return False

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

        interface_a.connected_endpoint_type = "dcim.interface"
        interface_z.connected_endpoint_type = "dcim.interface"

        item = self.default_create(object_type="cable", keys=keys, params=params)
        LOGGER.info("Created Cable %s (%s) in NetBox", item.get_unique_id(), cable.id)

        item.remote_id = cable.id
        return item

    def delete_cable(self, keys, params):  #  pylint: disable=unused-argument
        """Delete a Cable in NetBox

        Args:
            keys (dict): Dictionnary of primary keys of the object to delete
            params (dict): Dictionnary of attributes/parameters of the object to delete

        Returns:
            NetboxInterface: DSync object
        """
        item = self.cable(**keys)
        item = self.get(self.cable, keys=[item.get_unique_id()])

        cable = self.netbox.dcim.cables.get(item.remote_id)
        cable.delete()

        return cable

    # -----------------------------------------------------
    # Vlans
    # -----------------------------------------------------
    def create_vlan(self, keys, params):
        """Create new Vlan in NetBox

        Args:
            keys (dict): Dictionnary of primary keys of the object to create
            params (dict): Dictionnary of attributes/parameters of the object to create

        Returns:
            NetboxInterface: DSync object
        """
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

    def update_vlan(self, keys, params):
        """Update new Vlan in NetBox

        Args:
            keys (dict): Dictionnary of primary keys of the vlan to update
            params (dict): Dictionnary of attributes/parameters of the vlan to update

        Returns:
            NetboxInterface: DSync object
        """
        item = self.vlan(**keys)
        item = self.get(self.vlan, keys=[item.get_unique_id()])

        vlan = self.netbox.ipam.vlans.get(item.remote_id)
        vlan.update(data={"name": params["name"]})

        for key, value in params.items():
            setattr(item, key, value)

        return item

    # ----------------------------------------------
=======
        LOGGER.debug("%s | Found %s cables in netbox for %s", self.name, nbr_cables, site.name)
>>>>>>> develop-2.0

    def get_intf_from_netbox(self, device_name, intf_name):
        """Get an interface from NetBox based on the name of the device and the name of the interface.

        Exactly one return must be returned from NetBox, the function will return False if more than 1 result are returned.

        Args:
            device_name (str): name of the device in netbox
            intf_name (str): name of the interface in Netbox

        Returns:
            NetBoxInterface, bool: Interface in DSync format
        """
        intfs = self.netbox.dcim.interfaces.filter(name=intf_name, device=device_name)

        if len(intfs) == 0:
            LOGGER.debug("Unable to find the interface in NetBox for %s %s, nothing returned", device_name, intf_name)
            return False

        if len(intfs) > 1:
            LOGGER.warning(
                "Unable to find the proper interface in NetBox for %s %s, more than 1 element returned",
                device_name,
                intf_name,
            )
            return False

        intf = self.interface(name=intf_name, device_name=device_name, remote_id=intfs[0].id)

        if intfs[0].connected_endpoint_type:
            intf.connected_endpoint_type = intfs[0].connected_endpoint_type

        self.add(intf)

        return intf
