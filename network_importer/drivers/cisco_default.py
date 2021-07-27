"""default network_importer driver for cisco.

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

from nornir_netmiko.tasks import netmiko_send_command
from nornir.core.task import Result, Task
from nornir.core.exceptions import NornirSubTaskError

from netmiko.ssh_exception import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)

import network_importer.config as config
from network_importer.drivers.default import NetworkImporterDriver as DefaultNetworkImporterDriver
from network_importer.drivers.converters import (
    convert_cisco_genie_lldp_neighbors_details,
    convert_cisco_genie_cdp_neighbors_details,
    convert_cisco_genie_vlans,
)

LOGGER = logging.getLogger("network-importer")


class NetworkImporterDriver(DefaultNetworkImporterDriver):
    """Collection of Nornir Tasks specific to Cisco devices."""

    @staticmethod
    def get_config(task: Task) -> Result:
        """Get the latest configuration from the device using Netmiko.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        LOGGER.debug("Executing get_config for %s (%s)", task.host.name, task.host.platform)

        try:
            result = task.run(task=netmiko_send_command, command_string="show run", enable=True)
        except NornirSubTaskError as exc:
            if isinstance(exc.result.exception, NetmikoAuthenticationException):
                LOGGER.warning("Unable get the configuration because it can't connect to %s", task.host.name)
                return Result(host=task.host, failed=True, exception=exc.result.exception)

            if isinstance(exc.result.exception, NetmikoTimeoutException):
                LOGGER.warning("Unable get the configuration because the connection to %s timeout", task.host.name)
                return Result(host=task.host, failed=True, exception=exc.result.exception)

            LOGGER.debug("An exception occurred while pulling the configuration", exc_info=True)
            return Result(host=task.host, failed=True, exception=exc.result.exception)

        if result[0].failed:
            return result

        running_config = result[0].result

        if "ERROR: % Invalid input detected at" in running_config:
            LOGGER.warning("Unable to get the configuration for %s", task.host.name)
            return Result(host=task.host, failed=True)

        return Result(host=task.host, result={"config": running_config})

    @staticmethod
    def get_neighbors(task: Task) -> Result:
        """Get a list of neighbors from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the neighbors
            The format of the result but must be similar to Neighbors defined in network_importer.processors.get_neighbors
        """
        LOGGER.debug("Executing get_neighbor for %s (%s)", task.host.name, task.host.platform)

        if config.SETTINGS.main.import_cabling == "lldp":
            command = "show lldp neighbors detail"
            converter = convert_cisco_genie_lldp_neighbors_details
            cmd_type = "LLDP"
        elif config.SETTINGS.main.import_cabling == "cdp":
            command = "show cdp neighbors detail"
            converter = convert_cisco_genie_cdp_neighbors_details
            cmd_type = "CDP"
        else:
            return Result(host=task.host, failed=True)

        try:
            result = task.run(task=netmiko_send_command, command_string=command, use_genie=True)
        except NornirSubTaskError:
            LOGGER.debug("An exception occured while pulling %s data", cmd_type, exc_info=True)
            return Result(host=task.host, failed=True)

        if result[0].failed:
            return result

        results = converter(device_name=task.host.name, data=result[0].result)
        return Result(host=task.host, result=results.dict())

    @staticmethod
    def get_vlans(task: Task) -> Result:
        """Get a list of vlans from the device using netmiko and genie parser.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the vlans
            The format of the result but must be similar to Vlans defined in network_importer.processors.get_vlans
        """
        LOGGER.debug("Executing get_vlans for %s (%s)", task.host.name, task.host.platform)

        try:
            results = task.run(task=netmiko_send_command, command_string="show vlan", use_genie=True)
        except NornirSubTaskError:
            LOGGER.debug(
                "An exception occured while pulling the vlans information", exc_info=True,
            )
            return Result(host=task.host, failed=True)

        if not isinstance(results[0].result, dict) or "vlans" not in results[0].result:
            LOGGER.warning("%s | No vlans information returned", task.host.name)
            return Result(host=task.host, result=False)

        results = convert_cisco_genie_vlans(device_name=task.host.name, data=results[0].result)
        return Result(host=task.host, result=results.dict())
