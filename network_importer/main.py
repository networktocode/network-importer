"""
(c) 2019 Network To Code

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
# pylint: disable=R1724,W0611,R1710,R1710,E1101,W0613,C0103,C0413,R0904

import logging
import sys
import os
import re
import warnings
from collections import defaultdict
import ipaddress
import requests
import pynetbox

from jinja2 import Template, Environment, FileSystemLoader
from pybatfish.client.session import Session
from termcolor import colored

warnings.filterwarnings("ignore", category=DeprecationWarning)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from nornir import InitNornir
    from nornir.core.filter import F

import network_importer
from network_importer.drivers import get_driver
import network_importer.config as config
from network_importer.utils import sort_by_digits, patch_http_connection_pool
from network_importer.tasks import (
    initialize_devices,
    update_configuration,
    collect_transceivers_info,
    collect_vlans_info,
    collect_lldp_neighbors,
    device_update_remote,
    check_if_reachable,
    update_device_status,
)

from network_importer.model import (
    NetworkImporterDevice,
    NetworkImporterInterface,
    NetworkImporterSite,
    NetworkImporterVlan,
    NetworkImporterOptic,
    NetworkImporterCable,
)

from network_importer.base_model import Optic, Vlan, Cable, IPAddress

from network_importer.inventory import (
    valid_devs,
    non_valid_devs,
    reachable_devs,
    non_reachable_devs,
    valid_and_reachable_devs,
)

from network_importer.performance import timeit

__author__ = "Damien Garros <damien.garros@networktocode.com>"

logger = logging.getLogger("network-importer")


class NetworkImporter:
    """ """

    def __init__(self, check_mode=True):
        """


        Args:
          check_mode:  (Default value = True)

        Returns:

        """

        self.sites = dict()
        self.devs = None
        self.cables = dict()
        self.bf = None
        self.nb = None

        self.check_mode = check_mode

    def get_dev(self, dev_name):
        """
        Return the NI object for a given device_name

        Args:
          dev_name: Name of the device

        Returns:
          NetworkImporterDevice
        """

        if dev_name not in self.devs.inventory.hosts.keys():
            return False

        return self.devs.inventory.hosts[dev_name].data["obj"]

    @timeit
    def build_inventory(self, limit=None):
        """
        Build the inventory for the Network Importer in Nornir format
        # 1/ Devices already exist in Netbox
        #   Case A : configuration are provided
        #   Case B : configuration are not provided but primary IP is defined
        #
        # 2/ Devices are not in Netbox (Not Supported Yet)
        #   Everything is coming from inventory file
        #                 Mandatory: hostname, platform, username, password

        Args:
          limit: (Default value = None)

        Returns:

        """

        params = {}

        # ------------------------------------------------------------------------
        # Extract additional query filters if defined and convert string to dict
        #  Filters can be defined at the configuration level or in CLI or both
        # ------------------------------------------------------------------------

        if "inventory_filter" in config.main.keys():
            csparams = config.main["inventory_filter"].split(",")
            for csp in csparams:
                if "=" not in csp:
                    continue

                key, value = csp.split("=", 1)
                params[key] = value

        if limit:
            if "=" not in limit:
                params["name"] = limit

            else:
                csparams = limit.split(",")
                for csp in csparams:
                    if "=" not in csp:
                        continue
                    key, value = csp.split("=", 1)
                    params[key] = value

        if config.main["inventory_source"] == "netbox":
            self.devs = InitNornir(
                core={"num_workers": config.main["nbr_workers"]},
                logging={"enabled": False},
                inventory={
                    "plugin": "network_importer.inventory.NBInventory",
                    "options": {
                        "nb_url": config.netbox["address"],
                        "nb_token": config.netbox["token"],
                        "filter_parameters": params,
                        "ssl_verify": config.netbox["request_ssl_verify"],
                        "username": config.network["login"],
                        "password": config.network["password"],
                        "enable": config.network["enable"],
                        "supported_platforms": config.netbox["supported_platforms"],
                    },
                },
            )

        ## Second option in there but not really supported right now
        elif (
            config.main["inventory_source"] == "configs"
            and "configs_directory" in config.main.keys()
        ):

            ## TODO check if bf session has already been created, otherwise need to create it

            self.devs = InitNornir(
                core={"num_workers": config.main["nbr_workers"]},
                logging={"enabled": False},
                inventory={
                    "plugin": "network_importer.inventory.NornirInventoryFromBatfish",
                    "options": {"devices": self.bf.q.nodeProperties().answer().frame()},
                },
            )

        else:
            logger.critical(
                f"Unable to find an inventory please check the config file and the documentation"
            )
            sys.exit(1)

        return True

    @timeit
    def init(self, limit=None):
        """
        Initilize NetworkImporter Object
            Check if NB is reachable
            Create inventory
            Create all NetworkImporterDevice object
            Create all sites

        inputs:
            limit: filter the inventory to limit the execution to a subset of devices

        Args:
          limit: (Default value = None)

        Returns:

        """

        patch_http_connection_pool(maxsize=100)

        self.check_nb_params()
        self.init_bf_session()

        if not self.devs:
            self.build_inventory(limit=limit)

        # --------------------------------------------------------
        # Creating required directories on local filesystem
        # --------------------------------------------------------
        if (
            not self.check_mode
            and not os.path.exists(config.main["hostvars_directory"])
            and config.main["generate_hostvars"]
        ):
            os.makedirs(config.main["hostvars_directory"])
            logger.debug(
                f"Directory {config.main['hostvars_directory']} was missing, created it"
            )

        if not os.path.isdir(config.main["data_directory"]):
            os.mkdir(config.main["data_directory"])

        # --------------------------------------------------------
        # Initialize Devices
        #  - Create NID object
        #  - Pull cache information from Netbox
        # --------------------------------------------------------
        results = self.devs.run(task=initialize_devices, bfs=self.bf)

        for dev_name, items in results.items():
            if items[0].failed:
                logger.warning(
                    f"{dev_name} | Something went wrong while trying to initialize the device .. "
                )
                self.devs.inventory.hosts[dev_name].data["status"] = "fail-other"
                continue

        # --------------------------------------------------------
        # Initialize sites information
        #   Site information are pulled with devices
        #   TODO consider refactoring sites into a Nornir Inventory
        # Get all cables based on remote information
        # --------------------------------------------------------
        for dev in self.devs.inventory.hosts.values():

            if not dev.data["obj"].exist_remote:
                continue

            site_slug = dev.data["obj"].remote.site.slug

            ## Check if site and vlans information are already in cache
            if site_slug not in self.sites.keys():
                site = NetworkImporterSite(name=site_slug, nb=self.nb)
                self.sites[site.name] = site
                dev.data["obj"].site = site
                logger.debug(f"Created site {site.name}")

            else:
                dev.data["obj"].site = self.sites[site_slug]

            ## Get all remote cables and update cables inventory
            if config.main["import_cabling"]:
                remote_cables = dev.data["obj"].get_remote_cables()

                for cable_id, cable in remote_cables.items():
                    if cable_id not in self.cables:
                        self.cables[cable_id] = NetworkImporterCable(id=cable_id)
                        self.cables[cable_id].remote = cable

                    elif cable_id in self.cables and not self.cables[cable_id].remote:
                        self.cables[cable_id].remote = cable

        return True

    @timeit
    def import_devices_from_configs(self):
        """ """

        for host in self.devs.inventory.hosts.values():

            if not host.data["has_config"]:
                continue

            dev = host.data["obj"]

            logger.info(f"{dev.name} | Importing data from configurations .. ")

            bf_ints = self.bf.q.interfaceProperties(nodes=dev.name).answer()

            for bf_intf in bf_ints.frame().itertuples():
                found_intf = False

                intf_name = bf_intf.Interface.interface
                dev.add_batfish_interface(intf_name, bf_intf)

                for prfx in bf_intf.All_Prefixes:
                    if config.main["import_ips"]:
                        dev.add_ip(intf_name, IPAddress(address=prfx))

                    if config.main["import_prefixes"]:
                        dev.site.add_prefix_from_ip(ip=prfx)

            if config.main["import_vlans"] == "config":
                bf_vlans = self.bf.q.switchedVlanProperties(nodes=dev.name).answer()
                for vlan in bf_vlans.frame().itertuples():
                    dev.site.add_vlan(
                        vlan=Vlan(name=f"vlan-{vlan.VLAN_ID}", vid=vlan.VLAN_ID),
                        device=dev.name,
                    )

            if config.main["generate_hostvars"]:

                resp = self.bf.extract_facts(nodes=dev.name)
                if len(resp["nodes"].keys()) == 0:
                    logger.warning(f"{dev.name} | Unable to find hostvars ... ")
                elif len(resp["nodes"].keys()) != 1:
                    logger.warning(
                        f"{dev.name} | Unable to extract hostvars, more than 1 device returned ... "
                    )
                else:
                    dev.hostvars = list(resp["nodes"].values())[0]
                    del dev.hostvars["Interfaces"]

        return True

    @timeit
    def import_devices_from_cmds(self):
        """ """

        if not config.main["data_use_cache"]:
            self.devs.filter(filter_func=valid_and_reachable_devs).run(
                task=check_if_reachable, on_failed=True
            )

            self.warning_devices_not_reachable()

        if config.main["import_vlans"] == "cli":
            self.import_vlans_from_cmds()

        if config.main["import_transceivers"]:
            self.import_transceivers_from_cmds()

        return True

    def update_devices_status(self):
        """
        Update the status of the device on the remote system
        """

        self.devs.run(task=update_device_status, on_failed=True)

    def check_data_consistency(self):
        """
        After import, do some consistency validation on the data for:
        - Devices
        - Cables
        """

        # Devices
        for host in self.devs.inventory.hosts.keys():

            if not self.devs.inventory.hosts[host].data["has_config"]:
                continue

            self.get_dev(host).check_data_consistency()

        # Cabling
        self.validate_cabling()

    def check_nb_params(self, exit_on_failure=True):
        """
        TODO add support for non exist on failure

        Args:
          exit_on_failure: (Default value = True)

        Returns:

        """

        if not self.nb:
            self.__create_nb_handler()

        try:
            self.nb.dcim.devices.get(name="notpresent")
        except requests.exceptions.ConnectionError:
            logger.critical(
                f"Unable to connect to the netbox server ({config.netbox['address']})"
            )
            sys.exit(1)
        except pynetbox.core.query.RequestError as e:
            logger.critical(
                f"Unable to complete a query to the netbox server ({config.netbox['address']})"
            )
            print(e)
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            logger.critical(
                f"Unable to connect to the netbox server ({config.netbox['address']}), please check the address and the token"
            )
            print(e)
            sys.exit(1)

        return True

    @timeit
    def update_configurations(self):
        """
        Pull the latest configurations from all devices that are reachable
        Automatically cleanup the directory after to remove all configurations that have not been updated
        """

        logger.info("Updating configuration from devices .. ")

        if not os.path.isdir(config.main["configs_directory"]):
            os.mkdir(config.main["configs_directory"])
            logger.debug(
                f"Configs directory created at {config.main['configs_directory']}"
            )

        configs_dir_lvl2 = config.main["configs_directory"] + "/configs"

        if not os.path.isdir(configs_dir_lvl2):
            os.mkdir(configs_dir_lvl2)
            logger.debug(f"Configs directory created at {configs_dir_lvl2}")

        # Save the hostnames associated with all existing configurations before we start the update process
        hostname_existing_configs = [
            f.split(".txt")[0]
            for f in os.listdir(configs_dir_lvl2)
            if f.endswith(".txt")
        ]

        # ----------------------------------------------------
        # Do a pre-check to ensure that all devices are reachable
        # ----------------------------------------------------
        self.devs.filter(filter_func=reachable_devs).run(
            task=check_if_reachable, on_failed=True
        )
        self.warning_devices_not_reachable()

        results = self.devs.filter(filter_func=reachable_devs).run(
            task=update_configuration,
            configs_directory=configs_dir_lvl2,
            on_failed=True,
        )

        # ----------------------------------------------------
        # Process the results and identify which configs has not been updated
        # based on the list we captured previously
        # ----------------------------------------------------
        for dev_name, item in results.items():

            if not item[0].failed and dev_name in hostname_existing_configs:
                hostname_existing_configs.remove(dev_name)

            elif item[0].failed:
                logger.warning(
                    f"{dev_name} | Something went wrong while trying to update the configuration "
                )
                self.devs.inventory.hosts[dev_name].data["status"] = "fail-other"
                continue

        if len(hostname_existing_configs) > 0:
            logger.info(
                f"Will delete {len(hostname_existing_configs)} config(s) that have not been updated"
            )

            for f in hostname_existing_configs:
                os.remove(os.path.join(configs_dir_lvl2, f"{f}.txt"))

        return True

    def warning_devices_not_reachable(self, msg=""):
        """

        Args:
          msg: (Default value = "")

        Returns:

        """

        for host in self.devs.filter(
            filter_func=lambda h: h.data["is_reachable"] is False
        ).inventory.hosts:
            reason = self.devs.inventory.hosts[host].data.get(
                "not_reachable_reason", "reason not defined"
            )
            logger.warning(f"{host} device is not reachable, {reason}")

    @timeit
    def init_bf_session(self):
        """
        Initialize Batfish
        """

        CURRENT_DIRECTORY = os.getcwd().split("/")[-1]
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

        return True

    def diff_local_remote(self):
        """
        Check if a device is in sync between the local and the remote system and print the status
        """

        for dev_name in self.devs.inventory.hosts.keys():
            self.get_dev(dev_name).print_sync_status()

    def print_diffs(self):
        """ """

        for site in self.sites.values():
            diff = site.diff()
            if diff.has_diffs():
                diff.print_detailed()

        for host in self.devs.inventory.hosts.keys():
            dev = self.get_dev(host)

            if not self.devs.inventory.hosts[host].data["has_config"]:
                continue

            diff = dev.diff()
            if diff.has_diffs():
                diff.print_detailed()

        for cable in self.cables.values():
            if not cable.is_valid:
                continue

            diff = cable.diff()
            if diff.has_diffs():
                diff.print_detailed()

    @timeit
    def update_remote(self):
        """
        Update all objects on the remote system
          - 1/ Update the site and the vlans (serial)
          - 2/ Update all devices in parallel
          - 3/ Update all cables (serial)
        """

        # Site (serial)
        for site in self.sites.values():
            site.update_remote()

        # Devices (parallel)
        results = self.devs.filter(filter_func=valid_devs).run(
            task=device_update_remote
        )

        for dev_name, items in results.items():
            if items[0].failed:
                logger.warning(
                    f"{dev_name} | Something went wrong while trying to update the device in the remote system"
                )

                self.devs.inventory.hosts[dev_name].data["status"] = "fail-other"
                continue

        # Cables (serial)
        for cable in self.cables.values():
            cable.update_remote(self.nb)

        return True

    # --------------------------------------------------------------------------
    # Cabling
    # --------------------------------------------------------------------------

    def import_cabling(self):

        if config.main["import_cabling"] in ["no", False]:
            return False

        if config.main["import_cabling"] in ["config", True]:
            self.import_cabling_from_configs()

        if config.main["import_cabling"] in ["lldp", "cdp", True]:
            self.import_cabling_from_cmds()

        return True

    @timeit
    def import_cabling_from_configs(self):
        """
        Import cabling information from Batfish layer3Edges
        """

        p2p_links = self.bf.q.layer3Edges().answer()

        for link in p2p_links.frame().itertuples():

            self.__add_cable_local(
                dev_a=link.Interface.hostname,
                intf_a=re.sub(r"\.\d+$", "", link.Interface.interface),
                dev_z=link.Remote_Interface.hostname,
                intf_z=re.sub(r"\.\d+$", "", link.Remote_Interface.interface),
                source="config",
            )

        return True

    @timeit
    def import_cabling_from_cmds(self):

        logger.info("Collecting cabling information from devices .. ")

        results = self.devs.filter(filter_func=valid_and_reachable_devs).run(
            task=collect_lldp_neighbors,
            update_cache=config.main["data_update_cache"],
            use_cache=config.main["data_use_cache"],
            on_failed=True,
        )

        for dev_name, items in results.items():
            if items[0].failed:
                logger.warning(
                    f"{dev_name} | Something went wrong while trying to pull the lldp information"
                )
                self.devs.inventory.hosts[dev_name].data["status"] = "fail-other"
                continue

            if (
                not isinstance(items[0].result, dict)
                or "lldp_neighbors" not in items[0].result
            ):
                logger.warning(f"{dev_name} | No lldp information returned ")
                continue

            for interface, neighbors in items[0].result["lldp_neighbors"].items():

                if len(neighbors) > 1:
                    logger.warning(
                        f"{dev_name} | More than 1 neighbor found on interface {interface}, SKIPPING"
                    )
                    continue
                elif len(neighbors) == 1:

                    clean_name = neighbors[0]["hostname"].split(".")[0]

                    self.__add_cable_local(
                        dev_a=dev_name,
                        intf_a=interface,
                        dev_z=clean_name,
                        intf_z=neighbors[0]["port"],
                        source="lldp",
                    )

        return True

    @timeit
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

        for cable in self.cables.values():

            cable.is_valid = True

            for side in ["a", "z"]:

                dev_name, intf_name = cable.get_device_intf(side)

                if dev_name not in self.devs.inventory.hosts.keys():
                    logger.debug(
                        f"CABLE: {dev_name} not present in devices list ({side} side)"
                    )
                    cable.is_valid = False
                    cable.error = "missing-device"
                    continue

                dev = self.get_dev(dev_name)

                if intf_name not in dev.interfaces.keys():
                    logger.warning(
                        f"CABLE: {dev_name}:{intf_name} not present in interfaces list"
                    )
                    cable.is_valid = False
                    cable.error = "missing-interface"
                    continue

                if dev.interfaces[intf_name].is_virtual:
                    logger.debug(
                        f"CABLE: {dev_name}:{intf_name} is a virtual interface, can't be used for cabling SKIPPING ({side} side)"
                    )
                    cable.is_valid = False
                    cable.error = "virtual-interface"
                    continue

                cable.add_interface(dev.interfaces[intf_name])

                remote_side = "z"
                if side == "z":
                    remote_side = "a"

                remote_device_expected, remote_intf_expected = cable.get_device_intf(
                    remote_side
                )

                if (
                    not dev.interfaces[intf_name].remote
                    or not dev.interfaces[intf_name].remote.remote
                ):
                    continue

                cable_type = dev.interfaces[
                    intf_name
                ].remote.remote.connected_endpoint_type

                # Check if the interface is already connected
                # Check if it's already connected to the right device
                if not cable_type:
                    # Interface is currently not connected in netbox
                    continue

                elif cable_type != "dcim.interface":

                    logger.debug(
                        f"CABLE: {dev_name}:{intf_name} is already connected but to a different type of interface  ({cable_type})"
                    )
                    cable.is_valid = False
                    cable.error = "wrong-cable-type"
                    continue

                elif cable_type == "dcim.interface":
                    remote_host_reported = dev.interfaces[
                        intf_name
                    ].remote.remote.connected_endpoint.device.name
                    remote_int_reported = dev.interfaces[
                        intf_name
                    ].remote.remote.connected_endpoint.name

                    if remote_host_reported != remote_device_expected:
                        logger.warning(
                            f"CABLE: {dev_name}:{intf_name} is already connected but to a different device ({remote_host_reported} vs {remote_device_expected})"
                        )
                        cable.is_valid = False
                        cable.error = "wrong-peer-device"
                        continue

                    elif (
                        remote_host_reported == remote_device_expected
                        and remote_intf_expected != remote_int_reported
                    ):
                        logger.warning(
                            f"CABLE:  {dev_name}:{intf_name} is already connected but to a different interface ({remote_int_reported} vs {remote_intf_expected})"
                        )
                        cable.is_valid = False
                        cable.error = "interface-already-connected"
                        continue

        return True

    def update_cabling_remote(self):

        for cable in self.cables.values():

            cable.update_remote(self.nb)

    # --------------------------------------------------------------------------
    # Transceivers
    # --------------------------------------------------------------------------

    def import_transceivers_from_cmds(self):
        """ """

        logger.info("Collecting Transceiver information from devices .. ")

        results = self.devs.filter(filter_func=valid_and_reachable_devs).run(
            task=collect_transceivers_info,
            update_cache=config.main["data_update_cache"],
            use_cache=config.main["data_use_cache"],
            on_failed=True,
        )

        for dev_name, items in results.items():
            if items[0].failed:
                logger.warning(
                    f"{dev_name} | Something went wrong while trying to pull the transceiver information (1) "
                )
                self.devs.inventory.hosts[dev_name].data["status"] = "fail-other"
                continue

            transceivers = items[0].result

            if not isinstance(transceivers, list):
                logger.warning(
                    f"{dev_name} | Something went wrong while trying to pull the transceiver information (2)"
                )
                self.devs.inventory.hosts[dev_name].data["status"] = "fail-other"
                continue

            logger.info(f"{dev_name} | Found {len(transceivers)} transceivers")
            for transceiver in transceivers:

                nio = Optic(
                    name=transceiver["serial"].strip(),
                    optic_type=transceiver["type"].strip(),
                    intf=transceiver["interface"].strip(),
                    serial=transceiver["serial"].strip(),
                )

                self.devs.inventory.hosts[dev_name].data["obj"].add_optic(
                    intf_name=transceiver["interface"].strip(), optic=nio
                )

    # --------------------------------------------------------------------------
    # Vlans
    # --------------------------------------------------------------------------

    def import_vlans_from_cmds(self):

        logger.info("Collecting Vlan information from devices .. ")

        results = self.devs.filter(filter_func=valid_and_reachable_devs).run(
            task=collect_vlans_info,
            update_cache=config.main["data_update_cache"],
            use_cache=config.main["data_use_cache"],
            on_failed=True,
        )

        for dev_name, items in results.items():

            if items[0].failed:
                logger.warning(
                    f"{dev_name} | Something went wrong while trying to pull the vlan information"
                )
                self.devs.inventory.hosts[dev_name].data["status"] = "fail-other"
                continue

            for vlan in items[0].result:
                if (
                    vlan["id"]
                    not in self.devs.inventory.hosts[dev_name]
                    .data["obj"]
                    .site.vlans.keys()
                ):

                    self.devs.inventory.hosts[dev_name].data["obj"].site.add_vlan(
                        vlan=Vlan(name=vlan["name"], vid=vlan["id"]), device=dev_name,
                    )

    # --------------------------------------------------------------------------
    # Private methods
    # --------------------------------------------------------------------------

    def __add_cable_local(self, dev_a, intf_a, dev_z, intf_z, source=None):
        """
        Print on Screen all devices, interfaces and IPs and how their current status compare to remote
          Currently we only track PRESENT and ABSENT but we should also track DIFF and UPDATED
          This print function might be better off in the device object ...

        Args:
            dev_a: Name of the device on the side A of the cable
            intf_a:  Name of the interface on the side A of the cable
            dev_z: Name of the device on the side Z of the cable
            intf_z:  Name of the interface on the side Z of the cable
            source: origin of the data

        Returns:
            boolean:
                True if the cable has been properly added
                False if the cable was already present
        """

        cable = Cable(origin=source)
        cable.add_device(
            device=dev_a, interface=intf_a,
        )
        cable.add_device(
            device=dev_z, interface=intf_z,
        )

        if cable.unique_id and cable.unique_id not in self.cables:
            nic = NetworkImporterCable(id=cable.unique_id)
            nic.local = cable
            self.cables[cable.unique_id] = nic
            return True

        if cable.unique_id and cable.unique_id in self.cables:
            if not self.cables[cable.unique_id].local:
                self.cables[cable.unique_id].local = cable
                return True

        return False

    def __create_nb_handler(self):
        """ """

        self.nb = pynetbox.api(
            url=config.netbox["address"],
            token=config.netbox["token"],
            ssl_verify=config.netbox["request_ssl_verify"],
        )
        return True

    # def print_screen(self):
    #     """
    #     Print on Screen all devices, interfaces and IPs and how their current status compare to remote
    #       Currently we only track PRESENT and ABSENT but we should also track DIFF and UPDATED
    #       This print function might be better off in the device object ...

    #     Args:

    #     Returns:

    #     """
    #     PRESENT = colored("PRESENT", "green")
    #     ABSENT = colored("ABSENT", "yellow")

    #     for site in self.sites.values():
    #         print(f"-- Site {site.name} -- ")
    #         for vlan in site.vlans.values():
    #             if vlan.exist_remote:
    #                 print("{:4}{:32}{:12}".format("", f"Vlan {vlan.vid}", PRESENT))
    #             else:
    #                 print("{:4}{:32}{:12}".format("", f"Vlan {vlan.vid}", ABSENT))

    #         print("  ")

    #         for dev in self.devs.values():
    #             if dev.site.name != site.name:
    #                 continue
    #             if dev.exist_remote:
    #                 print("{:4}{:42}{:12}".format("", f"Device {dev.name}", PRESENT))
    #             else:
    #                 print("{:4}{:42}{:12}".format("", f"Device {dev.name}", ABSENT))

    #             for intf_name in sorted(dev.interfaces.keys(), key=sort_by_digits):
    #                 intf = dev.interfaces[intf_name]
    #                 if intf.exist_remote:
    #                     print("{:8}{:38}{:12}".format("", f"{intf.name}", PRESENT))
    #                 else:
    #                     print("{:8}{:38}{:12}".format("", f"{intf.name}", ABSENT))

    #                 for ip in intf.ips.values():
    #                     if ip.exist_remote:
    #                         print(
    #                             "{:12}{:34}{:12}".format("", f"{ip.address}", PRESENT)
    #                         )
    #                     else:
    #                         print("{:12}{:34}{:12}".format("", f"{ip.address}", ABSENT))
    #             print("  ")

    #     return True
