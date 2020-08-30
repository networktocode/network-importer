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

logger = logging.getLogger("network-importer")


class NetworkImporter(DSync):

    site = Site
    device = Device
    interface = Interface
    ip_address = IPAddress
    # cable = Cable
    # vlan = Vlan
    prefix = Prefix

    top_level = ["device"]

    nb = None

    def init(self, url, token, filters=None):

        self.nb = pynetbox.api(url=url, token=token, ssl_verify=False,)

        self.import_netbox_device(filters=filters)
        self.import_batfish()

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

        # self.bf.set_snapshot(SNAPSHOT_NAME)

        # Import Devices
        devices = self.get_all(self.device)
        # import pdb; pdb.set_trace()

        for device in devices:
            self.import_batfish_device(device=device)

        # devices = session.query(self.device).all()
        # logger.debug(f"Found {len(devices)} devices in Batfish")
        # self.import_batfish_cable(session)

    def import_batfish_device(self, device):
        """Import all devices from Batfish

        Args:
            device
        """
        # TODO > FIX > Temporarily disabled
        intfs = self.bf.q.interfaceProperties(nodes=device.name).answer().frame()
        for _, intf in intfs.iterrows():
            self.import_batfish_interface(device=device, intf=intf)

        # logger.debug(f"Add device {device.name} with {len(intfs)} interfaces from Batfish")

        # self.import_batfish_aggregate(device=device, session=session)

    def import_batfish_interface(self, device, intf):

        interface = self.interface(
            name=intf["Interface"].interface,
            device_name=device.name,
            description=intf["Description"],
        )
        self.add(interface)
        device.add_child(interface)

        for prefix in intf["All_Prefixes"]:

            ip_address = self.ip_address(
                address=prefix,
                device_name=device.name,
                interface_name=intf["Interface"].interface,
            )

            self.add(ip_address)
            interface.add_child(ip_address)

            # ip = session.query(self.ip_address).filter_by(
            #         address=prefix,
            #         device_name=device.name,
            #         interface_name=intf["Interface"].interface
            #     ).first()

            # if not ip:
            #     session.add(
            #         self.ip_address(

            #         )
            #     )
            # else:
            #     logger.warning(f"IP {prefix} {device.name} already present")

            # self.add_prefix_from_ip(ip=prefix, site=device.site, session=session)

    def add_prefix_from_ip(self, ip, site, session):

        prefix = ipaddress.ip_network(ip, strict=False)

        if prefix.num_addresses == 1:
            return False

        prefix_obj = (
            session.query(self.prefix).filter_by(prefix=str(prefix), site=site).first()
        )

        if not prefix_obj:
            session.add(self.prefix(prefix=str(prefix), site=site))
            logger.debug(f"Added Prefix {prefix} from batfish")

    def import_batfish_ip_address(self):
        pass

    def import_batfish_cable(self, session):

        p2p_links = self.bf.q.layer3Edges().answer()
        existing_cables = []
        for link in p2p_links.frame().itertuples():

            cable = self.cable(
                device_a_name=link.Interface.hostname,
                interface_a_name=re.sub(r"\.\d+$", "", link.Interface.interface),
                device_z_name=link.Remote_Interface.hostname,
                interface_z_name=re.sub(r"\.\d+$", "", link.Remote_Interface.interface),
            )
            uid = cable.unique_id()

            if uid not in existing_cables:
                session.add(cable)
                existing_cables.append(uid)

        nbr_cables = session.query(self.cable).count()
        logger.debug(f"Found {nbr_cables} cables in Batfish")

    def import_batfish_aggregate(self, device, session):

        aggregates = (
            self.bf.q.routes(protocols="aggregate", nodes=device.name).answer().frame()
        )

        for item in aggregates.itertuples():

            prefix_obj = (
                session.query(self.prefix)
                .filter_by(prefix=str(item.Network), site=device.site)
                .first()
            )

            if not prefix_obj:
                session.add(
                    self.prefix(
                        prefix=str(item.Network),
                        site=device.site,
                        prefix_type="AGGREGATE",
                    )
                )

                logger.debug(f"Added Aggregate prefix {item.Network}")
