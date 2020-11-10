"""main class for the network importer.

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

import network_importer.config as config
from network_importer.utils import patch_http_connection_pool
from network_importer.processors.get_config import GetConfig
from network_importer.drivers import dispatcher
from network_importer.diff import NetworkImporterDiff
from network_importer.tasks import check_if_reachable, warning_not_reachable
from network_importer.performance import timeit
from network_importer.inventory import (
    # valid_devs,
    # non_valid_devs,
    reachable_devs,
    # non_reachable_devs,
    # valid_and_reachable_devs,
)

warnings.filterwarnings("ignore", category=DeprecationWarning)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from nornir import InitNornir

__author__ = "Damien Garros <damien.garros@networktocode.com>"

LOGGER = logging.getLogger("network-importer")


class NetworkImporter:
    """Main NetworkImporter object to track all state related to the network importer."""

    def __init__(self, check_mode=False, nornir=None):
        """Initialize the NetworkImporter class."""
        self.nornir = nornir
        self.check_mode = check_mode
        self.network = None
        self.sot = None

    @timeit
    def build_inventory(self, limit=None):
        """Build the inventory for the Network Importer in Nornir format."""
        params = {}

        # ------------------------------------------------------------------------
        # Extract additional query filters if defined and convert string to dict
        #  Filters can be defined at the configuration level or in CLI or both
        # ------------------------------------------------------------------------
        if config.SETTINGS.inventory.filter:
            csparams = config.SETTINGS.inventory.filter.split(",")
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
            core={"num_workers": config.SETTINGS.main.nbr_workers},
            logging={"enabled": False},
            inventory={
                "plugin": config.SETTINGS.inventory.inventory_class,
                "options": {
                    "nb_url": config.SETTINGS.netbox.address,
                    "nb_token": config.SETTINGS.netbox.token,
                    "filter_parameters": params,
                    "ssl_verify": config.SETTINGS.netbox.verify_ssl,
                    "username": config.SETTINGS.network.login,
                    "password": config.SETTINGS.network.password,
                    "enable": config.SETTINGS.network.enable,
                    "use_primary_ip": config.SETTINGS.inventory.use_primary_ip,
                    "fqdn": config.SETTINGS.inventory.fqdn,
                    "supported_platforms": config.SETTINGS.netbox.supported_platforms,
                    "global_delay_factor": config.SETTINGS.network.global_delay_factor,
                    "banner_timeout": config.SETTINGS.network.banner_timeout,
                    "conn_timeout": config.SETTINGS.network.conn_timeout,
                },
            },
        )

        return True

    @timeit
    def init(self, limit=None):
        """Initilize NetworkImporter Object.

        Args:
          limit (str): (Default value = None)
        """
        patch_http_connection_pool(maxsize=100)

        if not self.nornir:
            self.build_inventory(limit=limit)

        # --------------------------------------------------------
        # Creating required directories on local filesystem
        # --------------------------------------------------------
        if (
            not self.check_mode
            and not os.path.exists(config.SETTINGS.main.hostvars_directory)
            and config.SETTINGS.main.generate_hostvars
        ):
            os.makedirs(config.SETTINGS.main.hostvars_directory)
            LOGGER.debug("Directory %s was missing, created it", config.SETTINGS.main.hostvars_directory)

        # --------------------------------------------------------
        # Initialize Adapters
        # --------------------------------------------------------
        LOGGER.info("Import SOT Model")
        sot_path = config.SETTINGS.adapters.sot_class.split(".")
        sot_params = config.SETTINGS.adapters.sot_params
        sot_adapter = getattr(importlib.import_module(".".join(sot_path[0:-1])), sot_path[-1])
        self.sot = sot_adapter(nornir=self.nornir, config=sot_params)
        self.sot.load()

        LOGGER.info("Import Network Model")
        network_adapter_path = config.SETTINGS.adapters.network_class.split(".")
        network_adapter_params = config.SETTINGS.adapters.network_params
        network_adapter = getattr(
            importlib.import_module(".".join(network_adapter_path[0:-1])), network_adapter_path[-1]
        )
        self.network = network_adapter(nornir=self.nornir, config=network_adapter_params)
        self.network.load()

        return True

    def sync(self):
        """Syncronize the SOT adapter and the network adapter."""
        self.sot.sync_from(self.network, diff_class=NetworkImporterDiff)

    def diff(self):
        """Generate a diff of the SOT adapter and the network adapter."""
        return self.sot.diff_from(self.network, diff_class=NetworkImporterDiff)

    @timeit
    def update_configurations(self):
        """Pull the latest configurations from all reachable devices.

        Automatically cleanup the directory after to remove all configurations that have not been updated
        """
        LOGGER.info("Updating configuration from devices .. ")

        # ----------------------------------------------------
        # Do a pre-check to ensure that all devices are reachable
        # ----------------------------------------------------
        self.nornir.filter(filter_func=reachable_devs).run(task=check_if_reachable, on_failed=True)
        self.nornir.filter(filter_func=reachable_devs).run(task=warning_not_reachable, on_failed=True)

        self.nornir.filter(filter_func=reachable_devs).with_processors([GetConfig()]).run(
            task=dispatcher, method="get_config", on_failed=True,
        )

        return True
