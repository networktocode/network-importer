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
import pynetbox
from itertools import count
from dsync import DSync
from dsync.exceptions import ObjectAlreadyExist
from .models import (
    NetboxSite,
    NetboxDevice,
    NetboxInterface,
    NetboxIPAddress,
    NetboxCable,
    NetboxPrefix,
    NetboxVlan,
)

import network_importer.config as config

logger = logging.getLogger("network-importer")

source = "NetBox"


class NetBoxAPIAdapter(DSync):

    site = NetboxSite
    device = NetboxDevice
    interface = NetboxInterface
    ip_address = NetboxIPAddress
    cable = NetboxCable
    vlan = NetboxVlan
    prefix = NetboxPrefix

    top_level = ["site", "device", "cable"]

    nb = None

    source = "NetBox"

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.nb = None

    def init(self, url, token, filters=None):

        self.nb = pynetbox.api(url=url, token=token, ssl_verify=False,)

        devices_list = self.import_netbox_device(filters)

        # Import Prefix and Vlan per site
        sites = self.get_all(self.site)
        for site in sites:
            self.import_netbox_prefix(site)
            self.import_netbox_vlan(site)
            self.import_netbox_cable(site, device_names=devices_list)

    def import_netbox_device(self, filters):
        """Import all devices from Netbox for a given filters. 

        Args:
            filters (dict): Pynetbox filter to apply when querying the list of devices to Netbox
        
        Returns:
            list: List of device names
        """
        nb_devs = self.nb.dcim.devices.filter(**filters)
        logger.debug(f"{source} | Found {len(nb_devs)} devices in netbox")
        device_names = []

        # -------------------------------------------------------------
        # Import Devices
        # -------------------------------------------------------------
        for device in nb_devs:

            if device.name in device_names:
                continue

            site = self.get("site", [device.site.slug])

            if not site:
                site = self.site(name=device.site.slug, remote_id=device.site.id)
                self.add(site)

            device = self.device(name=device.name, site_name=site.name, remote_id=device.id)
            self.add(device)

            # Store all devices name in a list to speed up later verification
            device_names.append(device.name)

        # -------------------------------------------------------------
        # Import Interface & IPs
        # -------------------------------------------------------------
        devices = self.get_all(self.device)
        logger.debug(f"{source} | Found {len(devices)} devices in memory")

        for dev in devices:
            self.import_netbox_interface(device=dev)
            self.import_netbox_ip_address(device=dev)

        return device_names

    def import_netbox_prefix(self, site):

        prefixes = self.nb.ipam.prefixes.filter(site=site.name, status="active")

        for nb_prefix in prefixes:
            prefix_type = None

            prefix = self.prefix(
                prefix=nb_prefix.prefix, site_name=site.name, prefix_type=prefix_type, remote_id=nb_prefix.id,
            )

            self.add(prefix)
            site.add_child(prefix)

    def import_netbox_vlan(self, site):

        vlans = self.nb.ipam.vlans.filter(site=site.name)

        for nb_vlan in vlans:

            vlan = self.vlan(vid=nb_vlan.vid, site_name=site.name, name=nb_vlan.name, remote_id=nb_vlan.id,)

            self.add(vlan)
            site.add_child(vlan)

    def import_netbox_interface(self, device):
        """Import all interfaces & Ips from Netbox for a given device. 

        Args:
            device (NetboxDevice): DSync object representing the device
        """

        # Import Interfaces
        intfs = self.nb.dcim.interfaces.filter(device=device.name)
        for intf in intfs:

            interface = self.interface(
                name=intf.name,
                device_name=device.name,
                remote_id=intf.id,
                description=intf.description or None,
                mtu=intf.mtu,
            )

            # Define status if it's enabled in the config file
            if config.main["import_intf_status"]:
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
                interface.allowed_vlans = [v.vid for v in intf.tagged_vlans]

            if intf.untagged_vlan:
                interface.access_vlan = intf.untagged_vlan.vid

            self.add(interface)
            device.add_child(interface)

        logger.debug(f"{self.source} | Found {len(intfs)} interfaces for {device.name}")

    def import_netbox_ip_address(self, device):

        ips = self.nb.ipam.ip_addresses.filter(device=device.name)
        for ip in ips:

            ip_address = self.ip_address(
                address=ip.address, device_name=device.name, interface_name=ip.interface.name, remote_id=ip.id,
            )

            self.add(ip_address)
            interface = self.get(self.interface, keys=[device.name, ip.interface.name])
            interface.add_child(ip_address)

        logger.debug(f"{self.source} | Found {len(ips)} ip addresses for {device.name}")

    def import_netbox_cable(self, site, device_names):

        cables = self.nb.dcim.cables.filter(site=site.name)

        nbr_cables = 0
        for nb_cable in cables:
            if nb_cable.termination_a_type != "dcim.interface" or nb_cable.termination_b_type != "dcim.interface":
                continue

            if nb_cable.termination_a.device.name not in device_names:
                logger.debug(
                    f"{source} | Skipping cable {nb_cable.id} because {nb_cable.termination_a.device.name} is not in the list of devices"
                )
                continue

            elif nb_cable.termination_b.device.name not in device_names:
                logger.debug(
                    f"{source} | Skipping cable {nb_cable.id} because {nb_cable.termination_b.device.name} is not in the list of devices"
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

        logger.debug(f"{self.source} | Found {nbr_cables} cables in netbox for {site.name}")

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

        nb_params = {}

        # Identify the id if the device this interface is attached to
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

        # if config.main["import_vlans"] != "no":
        #     if intf.local.mode in ["TRUNK", "ACCESS"] and intf.local.access_vlan:
        #         intf_properties["untagged_vlan"] = self.site.convert_vid_to_nid(
        #             intf.local.access_vlan
        #         )
        #     elif (
        #         intf.local.mode in ["TRUNK", "ACCESS"]
        #         and not intf.local.access_vlan
        #     ):
        #         intf_properties["untagged_vlan"] = None

        #     if (
        #         intf.local.mode in ["TRUNK", "L3_SUB_VLAN"]
        #         and intf.local.allowed_vlans
        #     ):
        #         intf_properties["tagged_vlans"] = self.site.convert_vids_to_nids(
        #             intf.local.allowed_vlans
        #         )
        #     elif (
        #         intf.local.mode in ["TRUNK", "L3_SUB_VLAN"]
        #         and not intf.local.allowed_vlans
        #     ):
        #         intf_properties["tagged_vlans"] = []

        if "is_lag_member" in params and params["is_lag_member"]:
            # TODO add checks to ensure the parent interface is present and has a remote id
            parent_interface = self.get(self.interface, keys=[device.name, nb_params["parent"]])
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

        intf = self.nb.dcim.interfaces.create(**nb_params)
        logger.debug(f"Created interface {intf.name} ({intf.id}) in NetBox")

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

        intf = self.nb.dcim.interfaces.get(item.remote_id)
        intf.update(data=nb_params)
        logger.debug(f"Updated Interface {item.device_name} {item.name} ({item.remote_id}) in NetBox")
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

        item = self.get(self.interface, list(keys.values()))
        intf = self.nb.dcim.interfaces.get(item.remote_id)
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
            ip_address = self.nb.ipam.ip_addresses.create(address=keys["address"], interface=interface.remote_id)
        else:
            ip_address = self.nb.ipam.ip_addresses.create(address=keys["address"])

        logger.debug(f"Created IP {ip_address.address} ({ip_address.id}) in NetBox")

        item = self.default_create(object_type="ip_address", keys=keys, params=params)
        item.remote_id = ip_address.id

        return item

    def delete_ip_address(self, keys, params):

        item = self.get(self.ip_address, list(keys.values()))

        ip = self.nb.ipam.ip_addresses.get(item.remote_id)
        ip.delete()

        item = self.default_delete(object_type="ip_address", keys=keys, params=params)

        return item

    # # -----------------------------------------------------
    # # Prefix
    # # -----------------------------------------------------
    def create_prefix(self, keys, params):

        site = self.get(self.site, keys=[keys["site_name"]])
        status = "active"

        prefix = self.nb.ipam.prefixes.create(prefix=keys["prefix"], site=site.remote_id, status=status)
        logger.debug(f"Created Prefix {prefix.prefix} ({prefix.id}) in NetBox")

        item = self.default_create(object_type="prefix", keys=keys, params=params)
        item.remote_id = prefix.id
        return item

    # -----------------------------------------------------
    # Cable
    # -----------------------------------------------------
    def create_cable(self, keys, params):

        interface_a = self.get(self.interface, keys=[keys["device_a_name"], keys["interface_a_name"]])
        interface_z = self.get(self.interface, keys=[keys["device_z_name"], keys["interface_z_name"]])

        try:
            cable = self.nb.dcim.cables.create(
                termination_a_type="dcim.interface",
                termination_b_type="dcim.interface",
                termination_a_id=interface_a.remote_id,
                termination_b_id=interface_z.remote_id,
            )
        except pynetbox.core.query.RequestError:
            logger.warning(f"Unable to create Cable {keys} in {self.source}")
            return False

        item = self.default_create(object_type="cable", keys=keys, params=params)
        logger.debug(f"Created Cable {item.get_unique_id()} ({cable.id}) in NetBox")

        item.remote_id = cable.id
        return item

    # -----------------------------------------------------
    # Vlans
    # -----------------------------------------------------
    def create_vlan(self, keys, params):

        logger.debug(f"TODO, implement create_vlan to add Vlan {keys} in NetBox")
        item = self.default_create(object_type="vlan", keys=keys, params=params)
        return item
