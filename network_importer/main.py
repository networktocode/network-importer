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
import os
import warnings
import importlib

warnings.filterwarnings("ignore", category=DeprecationWarning)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from nornir import InitNornir
    from nornir.core.filter import F

import network_importer.config as config

from network_importer.utils import sort_by_digits, patch_http_connection_pool
from network_importer.processors.get_config import GetConfig
from network_importer.processors.get_neighbors import GetNeighbors
from network_importer.drivers import dispatcher

from network_importer.tasks import check_if_reachable

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
                    "use_primary_ip": config.main["use_primary_ip"],
                    "fqdn": config.main["fqdn"],
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
        sot_path = config.main["sot_adapter"].split(".")
        sot_adapter = getattr(importlib.import_module(".".join(sot_path[0:-1])), sot_path[-1])
        self.sot = sot_adapter(nornir=self.nornir)
        self.sot.init()

        logger.info(f"Import Network Model")
        network_adapter_path = config.main["network_adapter"].split(".")
        network_adapter = getattr(
            importlib.import_module(".".join(network_adapter_path[0:-1])), network_adapter_path[-1]
        )
        self.network = network_adapter(nornir=self.nornir)
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

        # ----------------------------------------------------
        # Do a pre-check to ensure that all devices are reachable
        # ----------------------------------------------------
        self.nornir.filter(filter_func=reachable_devs).run(task=check_if_reachable, on_failed=True)
        self.warning_devices_not_reachable()

        results = (
            self.nornir.filter(filter_func=reachable_devs)
            .with_processors([GetConfig()])
            .run(task=dispatcher, method="get_config", on_failed=True,)
        )

        return True

    def warning_devices_not_reachable(self):
        """Generate warning logs for each unreachable device."""
        for host in self.nornir.filter(filter_func=lambda h: h.data["is_reachable"] is False).inventory.hosts:
            reason = self.nornir.inventory.hosts[host].data.get("not_reachable_reason", "reason not defined")
            logger.warning(f"{host} device is not reachable, {reason}")
