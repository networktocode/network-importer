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
import re
import warnings
import ipaddress
import requests
import pynetbox

from collections import defaultdict
import logging
from pybatfish.client.session import Session
from network_importer.adapters.base import BaseAdapter
from network_importer.models import *

import network_importer.config as config
from network_importer.utils import (
    is_interface_lag,
    is_interface_physical,
    expand_vlans_list,
)


from network_importer.inventory import reachable_devs
from network_importer.drivers import dispatcher
from network_importer.processors.get_neighbors import GetNeighbors

logger = logging.getLogger("network-importer")


class NetworkImporterAdapter(BaseAdapter):

    site = Site
    device = Device
    interface = Interface
    ip_address = IPAddress
    cable = Cable
    vlan = Vlan
    prefix = Prefix

    top_level = ["site", "device", "cable"]

    source = "Network"

    nb = None

    def init(self):

        sites = {}
        device_names = []

        # Create all devices and site object from Nornir Inventory
        for hostname, host in self.nornir.inventory.hosts.items():
            # if not host.data["has_config"]:
            #     continue

            if host.data["site"] not in sites.keys():
                site = self.site(name=host.data["site"])
                sites[host.data["site"]] = site
                self.add(site)
            else:
                site = sites[host.data["site"]]

            device = self.device(name=hostname, site_name=host.data["site"])
            self.add(device)

        self.import_batfish()
        self.import_cabling()

    def import_batfish(self):

        # CURRENT_DIRECTORY = os.getcwd().split("/")[-1]
        NETWORK_NAME = config.batfish["network_name"]
        SNAPSHOT_NAME = config.batfish["snapshot_name"]
        SNAPSHOT_PATH = config.main["configs_directory"]

        bf_params = dict(
            host=config.batfish["address"],
            port_v1=config.batfish["port_v1"],
            port_v2=config.batfish["port_v2"],
            ssl=config.batfish["use_ssl"],
        )
        if config.batfish["api_key"]:
            bf_params["api_key"] = config.batfish["api_key"]

        self.bf = Session.get("bf", **bf_params)
        self.bf.verify = False
        self.bf.set_network(NETWORK_NAME)
        self.bf.init_snapshot(SNAPSHOT_PATH, name=SNAPSHOT_NAME, overwrite=True)

        # Import Devices
        devices = self.get_all(self.device)

        for device in devices:
            self.import_batfish_device(device=device)

    def import_batfish_device(self, device):
        """Import all devices from Batfish

        Args:
            site
            device
        """

        site = self.get(self.site, keys=[device.site_name])

        interface_vlans_mapping = defaultdict(list)
        if config.main["import_vlans"] == "config":
            bf_vlans = self.bf.q.switchedVlanProperties(nodes=device.name).answer()
            for bf_vlan in bf_vlans.frame().itertuples():
                vlan = self.vlan(name=f"vlan-{bf_vlan.VLAN_ID}", vid=bf_vlan.VLAN_ID, site_name=site.name)
                self.add(vlan)
                site.add_child(vlan)

                # Save interface to vlan mapping for later use
                for intf in bf_vlan.Interfaces:
                    if intf.hostname != device.name.lower():
                        continue
                    interface_vlans_mapping[intf.interface].append(vlan.get_unique_id())

        intfs = self.bf.q.interfaceProperties(nodes=device.name).answer().frame()
        for _, intf in intfs.iterrows():
            self.import_batfish_interface(
                site=site,
                device=device,
                intf=intf,
                interface_vlans=interface_vlans_mapping[intf["Interface"].interface],
            )

    def import_batfish_interface(self, site, device, intf, interface_vlans=[]):
        """Import an interface for a given device from Batfish Data, including IP addresses and prefixes.

        Args:
            device (Device): Device object 
            intf (dict): Batfish interface object in Dict format
        """

        interface = self.interface(
            name=intf["Interface"].interface,
            device_name=device.name,
            description=intf["Description"] or None,
            mtu=intf["MTU"],
            switchport_mode=intf["Switchport_Mode"],
        )

        is_physical = is_interface_physical(interface.name)
        is_lag = is_interface_lag(interface.name)

        if is_lag:
            interface.is_lag = True
            interface.is_virtual = False
        elif is_physical == False:  # pylint: disable=C0121
            interface.is_virtual = True
        else:
            interface.is_virtual = False

        # if is_physical and interface.speed:
        # interface.speed = int(bf.Speed)

        if interface.switchport_mode == "FEX_FABRIC":
            interface.switchport_mode = "NONE"

        if config.main["import_intf_status"]:
            interface.active = intf["Active"]
        elif not config.main["import_intf_status"]:
            interface.active = None

        if interface.is_lag is None and interface.lag_members is None and len(list(intf["Channel_Group_Members"])) != 0:
            interface.lag_members = list(intf["Channel_Group_Members"])
            interface.is_lag = True
            interface.is_virtual = False
        elif interface.is_lag is None:
            interface.is_lag = False

        if interface.mode is None and interface.switchport_mode:
            if intf["Encapsulation_VLAN"]:
                interface.mode = "L3_SUB_VLAN"
                vlan, new = self.get_or_create_vlan(self.vlan(vid=intf["Encapsulation_VLAN"], site_name=site.name))
                interface.allowed_vlans = [vlan.get_unique_id()]
            else:
                interface.mode = interface.switchport_mode

        if interface.mode == "TRUNK":

            vids = expand_vlans_list(intf["Allowed_VLANs"])
            for vid in vids:
                vlan, new = self.get_or_create_vlan(self.vlan(vid=vid, site_name=site.name))
                interface.allowed_vlans.append(vlan.get_unique_id())

            if intf["Native_VLAN"]:
                native_vlan, new = self.get_or_create_vlan(self.vlan(vid=intf["Native_VLAN"], site_name=site.name))
                interface.access_vlan = native_vlan.get_unique_id()

        elif interface.mode == "ACCESS" and intf["Access_VLAN"]:
            vlan, new = self.get_or_create_vlan(self.vlan(vid=intf["Access_VLAN"], site_name=site.name))
            interface.access_vlan = vlan.get_unique_id()

        if interface.is_lag is False and interface.is_lag_member is None and intf["Channel_Group"]:
            interface.parent = self.interface(name=intf["Channel_Group"], device_name=device.name).get_unique_id()
            interface.is_lag_member = True
            interface.is_virtual = False

        self.add(interface)
        device.add_child(interface)

        for prefix in intf["All_Prefixes"]:
            self.import_batfish_ip_address(device, interface, prefix)

    def import_batfish_ip_address(self, device, interface, address, interface_vlans=[]):
        """Import IP address for a given interface from Batfish.

        Args:
            device (Device): Device object
            interface (Interface): Interface object 
            address (str): IP address in string format
        """

        ip_address = self.ip_address(address=address, device_name=device.name, interface_name=interface.name,)

        if config.main["import_ips"]:
            logger.debug(f"{self.source} | Import {ip_address.address} for {device.name}::{interface.name}")
            self.add(ip_address)
            interface.add_child(ip_address)

        if config.main["import_prefixes"]:
            vlan = None
            if len(interface_vlans) == 1:
                vlan = interface_vlans[0]
            elif len(interface_vlans) >= 1:
                logger.warning(
                    f"{device.name} | More than 1 vlan associated with interface {interface.name} ({interface_vlans})"
                )

            self.add_prefix_from_ip(ip_address=ip_address, site_name=device.site_name, vlan=vlan)

    def add_prefix_from_ip(self, ip_address, site_name=None, vlan=None):
        """Try to extract a prefix from an IP address and save it locally.

        Args:
            ip_address (IPAddress): DSync IPAddress object
            site_name (str, optional): Name of the site the prefix is part of. Defaults to None.
            vlan (str): Identifier of the vlan

        Returns:
            bool: False if a prefix can't be extracted from this IP address
        """

        prefix = ipaddress.ip_network(ip_address.address, strict=False)

        if prefix.num_addresses == 1:
            return False

        prefix_obj = self.get(self.prefix, keys=[site_name, str(prefix)])

        if not prefix_obj:
            prefix_obj = self.prefix(prefix=str(prefix), site_name=site_name, vlan=vlan)
            self.add(prefix_obj)
            logger.debug(f"Added Prefix {prefix} from batfish")

        if prefix_obj and vlan and not prefix_obj.vlan:
            prefix_obj.vlan = vlan
            logger.debug(f"Updated Prefix {prefix} with vlan {vlan}")

        return True

    def import_cabling(self):

        if config.main["import_cabling"] in ["no", False]:
            return False

        if config.main["import_cabling"] in ["config", True]:
            self.import_batfish_cable()

        if config.main["import_cabling"] in ["lldp", "cdp", True]:
            self.import_cabling_from_cmds()

        self.validate_cabling()

        return True

    def import_batfish_cable(self):
        """Import cables from Batfish using layer3Edges tables."""

        device_names = [device.name for device in self.get_all(self.device)]
        p2p_links = self.bf.q.layer3Edges().answer()
        existing_cables = []
        for link in p2p_links.frame().itertuples():

            if link.Interface.hostname not in device_names:
                continue

            if link.Remote_Interface.hostname not in device_names:
                continue

            cable = self.cable(
                device_a_name=link.Interface.hostname,
                interface_a_name=re.sub(r"\.\d+$", "", link.Interface.interface),
                device_z_name=link.Remote_Interface.hostname,
                interface_z_name=re.sub(r"\.\d+$", "", link.Remote_Interface.interface),
                source="batfish",
            )
            uid = cable.get_unique_id()

            if uid not in existing_cables:
                self.add(cable)
                existing_cables.append(uid)

        nbr_cables = len(self.get_all(self.cable))
        logger.debug(f"Found {nbr_cables} cables in Batfish")

    def import_cabling_from_cmds(self):
        """Import cabling information from the CLI, either using LDLP or CDP based on the configuration.

        If the FQDN is defined, and the hostname of a neighbor include the FQDN, remove it.
        """
        logger.info("Collecting cabling information from devices .. ")

        results = (
            self.nornir.filter(filter_func=reachable_devs)
            .with_processors([GetNeighbors()])
            .run(task=dispatcher, method="get_neighbors", on_failed=True,)
        )

        nbr_cables = 0
        for dev_name, items in results.items():
            if items[0].failed:
                continue

            if not isinstance(items[1][0].result, dict) or "neighbors" not in items[1][0].result:
                logger.debug(f"{dev_name} | No neighbors information returned SKIPPING ")
                continue

            for interface, neighbors in items[1][0].result["neighbors"].items():
                cable = self.cable(
                    device_a_name=dev_name,
                    interface_a_name=interface,
                    device_z_name=neighbors[0]["hostname"],
                    interface_z_name=neighbors[0]["port"],
                    source="cli",
                )
                nbr_cables += 1
                logger.debug(f"{dev_name} | Added cable {cable.get_unique_id()}")
                self.get_or_add(cable)

        logger.debug(f"Found {nbr_cables} cables from Cli")

    def validate_cabling(self):
        """
        Check if all cables are valid
            Check if both devices are present in the device list
                For now only process cables with both devices present
            Check if both interfaces are present as well and are not virtual
            Check that both interfaces are not already connected to a different device/interface

        When a cable is not valid, update the flag valid on the object itself
        Non valid cables will be ignored later on for update/creation
        """
        cables = self.get_all(self.cable)
        for cable in list(cables):

            for side in ["a", "z"]:

                dev_name, intf_name = cable.get_device_intf(side)

                dev = self.get(self.device, keys=[dev_name])

                if not dev:
                    logger.debug(f"CABLE: {dev_name} not present in devices list ({side} side)")
                    self.delete(cable)
                    continue

                intf = self.get(self.interface, keys=[dev_name, intf_name])

                if not intf:
                    logger.warning(f"CABLE: {dev_name}:{intf_name} not present in interfaces list")
                    self.delete(cable)
                    continue

                if intf.is_virtual:
                    logger.debug(
                        f"CABLE: {dev_name}:{intf_name} is a virtual interface, can't be used for cabling SKIPPING ({side} side)"
                    )
                    self.delete(cable)
                    continue

                # remote_side = "z"
                # if side == "z":
                #     remote_side = "a"

                # remote_device_expected, remote_intf_expected = cable.get_device_intf(remote_side)

                # remote_dev = self.get(self.device, keys=[remote_device_expected])

                # if not dev.interfaces[intf_name].remote or not dev.interfaces[intf_name].remote.remote:
                #     continue

                # cable_type = dev.interfaces[intf_name].remote.remote.connected_endpoint_type

                # # Check if the interface is already connected
                # # Check if it's already connected to the right device
                # if not cable_type:
                #     # Interface is currently not connected in netbox
                #     continue

                # elif cable_type != "dcim.interface":

                #     logger.debug(
                #         f"CABLE: {dev_name}:{intf_name} is already connected but to a different type of interface  ({cable_type})"
                #     )
                #     cable.is_valid = False
                #     cable.error = "wrong-cable-type"
                #     continue

                # elif cable_type == "dcim.interface":
                #     remote_host_reported = dev.interfaces[intf_name].remote.remote.connected_endpoint.device.name
                #     remote_int_reported = dev.interfaces[intf_name].remote.remote.connected_endpoint.name

                #     if remote_host_reported != remote_device_expected:
                #         logger.warning(
                #             f"CABLE: {dev_name}:{intf_name} is already connected but to a different device ({remote_host_reported} vs {remote_device_expected})"
                #         )
                #         cable.is_valid = False
                #         cable.error = "wrong-peer-device"
                #         continue

                #     elif remote_host_reported == remote_device_expected and remote_intf_expected != remote_int_reported:
                #         logger.warning(
                #             f"CABLE:  {dev_name}:{intf_name} is already connected but to a different interface ({remote_int_reported} vs {remote_intf_expected})"
                #         )
                #         cable.is_valid = False
                #         cable.error = "interface-already-connected"
                #         continue
