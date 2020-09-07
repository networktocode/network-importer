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
import sys
import os
import re
import warnings
from collections import defaultdict
import ipaddress
import requests
import pynetbox

from jinja2 import Template, Environment, FileSystemLoader

warnings.filterwarnings("ignore", category=DeprecationWarning)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from nornir import InitNornir
    from nornir.core.filter import F

import network_importer.config as config

from network_importer.utils import sort_by_digits, patch_http_connection_pool
from network_importer.tasks import (
    # initialize_devices,
    update_configuration,
    # collect_transceivers_info,
    # collect_vlans_info,
    # collect_lldp_neighbors,
    # device_update_remote,
    check_if_reachable,
    # update_device_status,
)

from network_importer.inventory import (
    valid_devs,
    non_valid_devs,
    reachable_devs,
    non_reachable_devs,
    valid_and_reachable_devs,
)

from network_importer.adapters.netbox_api import NetBoxAPIAdapter
from network_importer.adapters.network_importer import NetworkImporterAdapter
from network_importer.performance import timeit

__author__ = "Damien Garros <damien.garros@networktocode.com>"

logger = logging.getLogger("network-importer")


class NetworkImporter:
    def __init__(self, check_mode=False, nornir=None):

        self.nornir = nornir
        self.check_mode = check_mode
        self.network = None
        self.sot = None

    # @timeit
    def build_inventory(self, limit=None):
        """
        Build the inventory for the Network Importer in Nornir format
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

        # TODO Cleanup config file and allow user define inventory
        self.nornir = InitNornir(
            core={"num_workers": config.main["nbr_workers"]},
            logging={"enabled": False},
            inventory={
                "plugin": "network_importer.inventory.NetboxInventory",
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

        if not self.nornir:
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
            logger.debug(f"Directory {config.main['hostvars_directory']} was missing, created it")

        if not os.path.isdir(config.main["data_directory"]):
            os.mkdir(config.main["data_directory"])

        # --------------------------------------------------------
        # Initialize Object
        # TODO allow user defined class
        # --------------------------------------------------------

        logger.info(f"Import SOT Model")
        self.sot = NetBoxAPIAdapter(nornir=self.nornir)
        self.sot.init()

        logger.info(f"Import Network Model")
        self.network = NetworkImporterAdapter(nornir=self.nornir)
        self.network.init()

        return True

    def sync(self):
        self.sot.sync(self.network)

    def diff(self):
        return self.sot.diff(self.network)

    @timeit
    def update_configurations(self):
        """
        Pull the latest configurations from all devices that are reachable
        Automatically cleanup the directory after to remove all configurations that have not been updated
        """

        logger.info("Updating configuration from devices .. ")

        if not os.path.isdir(config.main["configs_directory"]):
            os.mkdir(config.main["configs_directory"])
            logger.debug(f"Configs directory created at {config.main['configs_directory']}")

        configs_dir_lvl2 = config.main["configs_directory"] + "/configs"

        if not os.path.isdir(configs_dir_lvl2):
            os.mkdir(configs_dir_lvl2)
            logger.debug(f"Configs directory created at {configs_dir_lvl2}")

        # Save the hostnames associated with all existing configurations before we start the update process
        hostname_existing_configs = [f.split(".txt")[0] for f in os.listdir(configs_dir_lvl2) if f.endswith(".txt")]

        # ----------------------------------------------------
        # Do a pre-check to ensure that all devices are reachable
        # ----------------------------------------------------
        self.nornir.filter(filter_func=reachable_devs).run(task=check_if_reachable, on_failed=True)
        self.warning_devices_not_reachable()

        results = self.devs.filter(filter_func=reachable_devs).run(
            task=update_configuration, configs_directory=configs_dir_lvl2, on_failed=True,
        )

        # ----------------------------------------------------
        # Process the results and identify which configs has not been updated
        # based on the list we captured previously
        # ----------------------------------------------------
        for dev_name, item in results.items():

            if not item[0].failed and dev_name in hostname_existing_configs:
                hostname_existing_configs.remove(dev_name)

            elif item[0].failed:
                logger.warning(f"{dev_name} | Something went wrong while trying to update the configuration ")
                self.nornir.inventory.hosts[dev_name].data["status"] = "fail-other"
                continue

        if len(hostname_existing_configs) > 0:
            logger.info(f"Will delete {len(hostname_existing_configs)} config(s) that have not been updated")

            for f in hostname_existing_configs:
                os.remove(os.path.join(configs_dir_lvl2, f"{f}.txt"))

        return True
