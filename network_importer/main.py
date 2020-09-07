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

from jinja2 import Template, Environment, FileSystemLoader
from termcolor import colored
import logging
from pybatfish.client.session import Session
from dsync import DSync
from .models import *

import network_importer.config as config
from network_importer.utils import (
    is_interface_lag,
    is_interface_physical,
    expand_vlans_list,
)

logger = logging.getLogger("network-importer")


class NetworkImporter(DSync):

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

    def init(self, url, token, filters=None):

        self.nb = pynetbox.api(url=url, token=token, ssl_verify=False,)

        self.import_netbox_device(filters=filters)
        self.import_batfish()

        self.import_cabling()

    def import_netbox_device(self, filters):

        nb_devs = self.nb.dcim.devices.filter(**filters)
        logger.debug(f"Found {len(nb_devs)} devices in netbox")
        device_names = []

        # -------------------------------------------------------------
        # Import Devices
        # -------------------------------------------------------------
        for device in nb_devs:

            if device.name in device_names:
                continue

            site = self.get("site", [device.site.slug])

            if not site:
                site = self.site(name=device.site.slug)
                self.add(site)

            device = self.device(name=device.name, site_name=site.name)
            self.add(device)
            device_names.append(device.name)

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
            device
        """
        intfs = self.bf.q.interfaceProperties(nodes=device.name).answer().frame()
        for _, intf in intfs.iterrows():
            self.import_batfish_interface(device=device, intf=intf)

        # logger.debug(f"Add device {device.name} with {len(intfs)} interfaces from Batfish")
        # self.import_batfish_aggregate(device=device, session=session)

    def import_batfish_interface(self, device, intf):
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

        if (
            interface.is_lag is None
            and interface.lag_members is None
            and len(list(intf["Channel_Group_Members"])) != 0
        ):
            interface.lag_members = list(intf["Channel_Group_Members"])
            interface.is_lag = True
            interface.is_virtual = False
        elif interface.is_lag is None:
            interface.is_lag = False

        if interface.mode is None and interface.switchport_mode:
            if intf["Encapsulation_VLAN"]:
                interface.mode = "L3_SUB_VLAN"
                interface.allowed_vlans = [intf["Encapsulation_VLAN"]]
            else:
                interface.mode = interface.switchport_mode

        if interface.mode == "TRUNK":
            interface.allowed_vlans = expand_vlans_list(intf["Allowed_VLANs"])
            if intf["Native_VLAN"]:
                interface.access_vlan = intf["Native_VLAN"]

        elif interface.mode == "ACCESS" and intf["Access_VLAN"]:
            interface.access_vlan = intf["Access_VLAN"]

        if (
            interface.is_lag is False
            and interface.is_lag_member is None
            and intf["Channel_Group"]
        ):
            interface.parent = intf["Channel_Group"]
            interface.is_lag_member = True
            interface.is_virtual = False

        self.add(interface)
        device.add_child(interface)

        for prefix in intf["All_Prefixes"]:
            self.import_batfish_ip_address(device, interface, prefix)

    def import_batfish_ip_address(self, device, interface, address):
        """Import IP address for a given interface from Batfish.

        Args:
            device (Device): Device object
            interface (Interface): Interface object 
            address (str): IP address in string format
        """

        ip_address = self.ip_address(
            address=address, device_name=device.name, interface_name=interface.name,
        )
        logger.debug(
            f"{self.source} | Import {ip_address.address} for {device.name}::{interface.name}"
        )
        self.add(ip_address)
        interface.add_child(ip_address)

        self.add_prefix_from_ip(ip_address=ip_address, site_name=device.site_name)

    def add_prefix_from_ip(self, ip_address, site_name=None):
        """Try to extract a prefix from an IP address and save it locally.

        Args:
            ip_address (IPAddress): DSync IPAddress object
            site_name (str, optional): Name of the site the prefix is part of. Defaults to None.

        Returns:
            bool: False if a prefix can't be extracted from this IP address
        """

        prefix = ipaddress.ip_network(ip_address.address, strict=False)

        if prefix.num_addresses == 1:
            return False

        prefix_obj = self.get(self.prefix, keys=[site_name, str(prefix)])

        if not prefix_obj:
            prefix_obj = self.prefix(prefix=str(prefix), site_name=site_name)
            self.add(prefix_obj)
            logger.debug(f"Added Prefix {prefix} from batfish")

        return True

    def import_cabling(self):

        if config.main["import_cabling"] in ["no", False]:
            return False

        if config.main["import_cabling"] in ["config", True]:
            self.import_batfish_cable()

        if config.main["import_cabling"] in ["lldp", "cdp", True]:
            pass
            # self.import_cabling_from_cmds()

        return True

    def import_batfish_cable(self):
        """Import cables from Batfish using layer3Edges tables."""

        p2p_links = self.bf.q.layer3Edges().answer()
        existing_cables = []
        for link in p2p_links.frame().itertuples():

            cable = self.cable(
                device_a_name=link.Interface.hostname,
                interface_a_name=re.sub(r"\.\d+$", "", link.Interface.interface),
                device_z_name=link.Remote_Interface.hostname,
                interface_z_name=re.sub(r"\.\d+$", "", link.Remote_Interface.interface),
            )
            uid = cable.get_unique_id()

            if uid not in existing_cables:
                self.add(cable)
                existing_cables.append(uid)

        nbr_cables = len(self.get_all(self.cable))
        logger.debug(f"Found {nbr_cables} cables in Batfish")

    # def import_batfish_aggregate(self, device, session):

    #     aggregates = (
    #         self.bf.q.routes(protocols="aggregate", nodes=device.name).answer().frame()
    #     )

    #     for item in aggregates.itertuples():

    #         prefix_obj = (
    #             session.query(self.prefix)
    #             .filter_by(prefix=str(item.Network), site=device.site)
    #             .first()
    #         )

    #         if not prefix_obj:
    #             session.add(
    #                 self.prefix(
    #                     prefix=str(item.Network),
    #                     site=device.site,
    #                     prefix_type="AGGREGATE",
    #                 )
    #             )

    #             logger.debug(f"Added Aggregate prefix {item.Network}")
