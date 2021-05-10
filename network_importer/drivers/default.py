"""default driver for the network_importer.

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

from nornir_napalm.plugins.tasks import napalm_get
from nornir_netmiko.tasks import netmiko_send_command

from nornir.core.task import Result, Task
from nornir.core.exceptions import NornirSubTaskError

import network_importer.config as config
from network_importer.drivers.converters import convert_cisco_genie_cdp_neighbors_details

LOGGER = logging.getLogger("network-importer")


class NetworkImporterDriver:
    """Default collection of Nornir Tasks based on Napalm."""

    @staticmethod
    def get_config(task: Task) -> Result:
        """Get the latest configuration from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        LOGGER.debug("Executing get_config for %s (%s)", task.host.name, task.host.platform)

        try:
            result = task.run(task=napalm_get, getters=["config"], retrieve="running")
        except:  # noqa: E722 # pylint: disable=bare-except
            LOGGER.debug("An exception occured while pulling the configuration", exc_info=True)
            return Result(host=task.host, failed=True)

        if result[0].failed:
            return result

        running_config = result[0].result.get("config", {}).get("running", None)
        return Result(host=task.host, result={"config": running_config})

    @staticmethod
    def get_neighbors(task: Task) -> Result:  # pylint: disable=too-many-return-statements
        """Get a list of neighbors from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the neighbors
            The format of the result but must be similar to Neighbors defined in network_importer.processors.get_neighbors
        """
        LOGGER.debug("Executing get_neighbor for %s (%s)", task.host.name, task.host.platform)

        if config.SETTINGS.main.import_cabling == "lldp":

            try:
                result = task.run(task=napalm_get, getters=["lldp_neighbors"])
            except:  # noqa: E722 # pylint: disable=bare-except
                LOGGER.debug("An exception occured while pulling lldp_data", exc_info=True)
                return Result(host=task.host, failed=True)

            if result[0].failed:
                return result

            neighbors = result[0].result.get("lldp_neighbors", {})
            return Result(host=task.host, result={"neighbors": neighbors})

        if config.SETTINGS.main.import_cabling == "cdp":

            try:
                result = task.run(task=netmiko_send_command, command_string="show cdp neighbors detail", use_genie=True)
            except NornirSubTaskError:
                LOGGER.debug("An exception occured while pulling CDP data")
                return Result(host=task.host, failed=True)

            if result[0].failed:
                return result

            results = convert_cisco_genie_cdp_neighbors_details(device_name=task.host.name, data=result[0].result)
            return Result(host=task.host, result=results.dict())

        LOGGER.warning("%s | Unexpected value for `import_cabling`, should be either LLDP or CDP", task.host.name)
        return Result(host=task.host, failed=True)

    @staticmethod
    def get_vlans(task: Task) -> Result:
        """Placeholder for get_vlans Get a list of vlans from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the vlans
            The format of the result but must be similar to Vlans defined in network_importer.processors.get_vlans
        """
        LOGGER.warning("%s | Get Vlans not implemented in the default driver.", task.host.name)
