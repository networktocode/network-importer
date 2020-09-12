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
import pdb
from collections import defaultdict
from nornir.plugins.tasks.networking import napalm_get, netmiko_send_command
from nornir.core.task import AggregatedResult, MultiResult, Result, Task

import network_importer.config as config

logger = logging.getLogger("network-importer")


class NetworkImporterDriver:
    @staticmethod
    def get_config(task: Task) -> Result:
        """Get the latest configuration from the device. 

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        logger.debug(f"Executing get_config for {task.host.name} ({task.host.platform})")

        try:
            result = task.run(task=napalm_get, getters=["config"], retrieve="running")
        except:
            logger.debug("An exception occured while pulling the configuration", exc_info=True)
            return Result(host=task.host, failed=True)

        if result[0].failed:
            return result

        running_config = result[0].result.get("config", {}).get("running", None)
        return Result(host=task.host, result={"config": running_config})

    @staticmethod
    def get_neighbors(task: Task) -> Result:
        logger.debug(f"Executing get_neighbor for {task.host.name} ({task.host.platform})")

        if config.main["import_cabling"] == "lldp":

            try:
                result = task.run(task=napalm_get, getters=["lldp_neighbors"])
            except:
                logger.debug("An exception occured while pulling lldp_data", exc_info=True)
                return Result(host=task.host, failed=True)

            if result[0].failed:
                return result

            neighbors = result[0].result.get("lldp_neighbors", {})
            return Result(host=task.host, result={"neighbors": neighbors})

        elif config.main["import_cabling"] == "cdp":
            try:
                results = task.run(
                    task=netmiko_send_command, command_string="show cdp neighbors detail", use_textfsm=True,
                )
            except:
                logger.debug("An exception occured while pulling cdp_data", exc_info=True)
                return Result(host=task.host, failed=True)

            neighbors = defaultdict(list)

            # Convert CDP details output to Napalm LLDP format
            if not isinstance(results[0].result, list):
                logger.warning(f"{task.host.name} | No CDP information returned")
            else:
                for neighbor in results[0].result:
                    neighbor_hostname = neighbor.get("destination_host") or neighbor.get("dest_host")
                    neighbor_port = neighbor["remote_port"]

                    neighbors[neighbor["local_port"]].append(dict(hostname=neighbor_hostname, port=neighbor_port,))

            return Result(host=task.host, result={"neighbors": neighbors})
