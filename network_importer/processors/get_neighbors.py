"""GetNeighbors processor for the network_importer.

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
from collections import defaultdict
import logging
import re

from typing import Dict, List

from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Task
from pydantic import BaseModel  # pylint: disable=no-name-in-module

import network_importer.config as config
from network_importer.processors import BaseProcessor
from network_importer.utils import is_mac_address

LOGGER = logging.getLogger("network-importer")

# Possible Junos port names xe-0/0/1.0, xe-0/0/3:0, ge, et, em sxe, fte, me, fc, xle
# Match the incorrectly capitalized interface names
JUNOS_INTERFACE_PATTERN = re.compile(r"^(Xe|Ge|Et|Em|Sxe|Fte|Me|Fc|Xle)-\d+/\d+/\d+[.:]*\d*$")


# -----------------------------------------------------------------
# Inventory Filter functions
# -----------------------------------------------------------------
def hosts_for_cabling(host):
    """Inventory Filter for Nornir.

    Return True or False if a device is eligible for cabling.
    It's using config.SETTINGS.main.excluded_platforms_cabling to determine if a host is eligible.

    Args:
      host(Host): Nornir Host

    Returns:
        bool: True if the device is eligible for cabling, False otherwise.
    """
    if host.platform in config.SETTINGS.main.excluded_platforms_cabling:
        return False

    return True


# -----------------------------------------------------------------
# Expected Returned Data
# -----------------------------------------------------------------
class Neighbor(BaseModel):
    """Dataclass model to store one Neighbor returned by get_neighbors."""

    hostname: str
    port: str


class Neighbors(BaseModel):
    """Dataclass model to store all Neighbors returned by get_neighbors."""

    neighbors: Dict[str, List[Neighbor]] = defaultdict(list)


# -----------------------------------------------------------------
# Processor
# -----------------------------------------------------------------
class GetNeighbors(BaseProcessor):
    """GetNeighbors processor for the network_importer."""

    task_name = "get_neighbors"

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Before getting the new configuration, check if a configuration already exist and calculate its md5.

        Args:
            task (Task): Nornir Task
            host (Host): Nornir Host
        """
        if task.name != self.task_name:
            return

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """For each host, check if the results returned by the task is valid and cleanup results as needed.

        Args:
            task (Task): Nornir Task
            host (Host): Nornir Host
            result (MultiResult): Nornir Results
        """
        if task.name != self.task_name:
            return

        if result[0].failed:
            LOGGER.warning("%s | Something went wrong while trying to pull the neighbor information", host.name)
            host.status = "fail-other"
            return

        if not isinstance(result[0].result, dict) or "neighbors" not in result[0].result:
            LOGGER.warning("%s | No neighbor information returned", host.name)
            result[0].failed = True
            return

        interfaces = list(result[0].result["neighbors"].keys())
        for interface in interfaces:

            neighbors = result[0].result["neighbors"][interface]

            if len(neighbors) > 1:
                LOGGER.warning("%s | More than 1 neighbor found on interface %s, SKIPPING", host.name, interface)
                del result[0].result["neighbors"][interface]
                continue

            if is_mac_address(neighbors[0]["hostname"]):
                del result[0].result["neighbors"][interface]
                continue

            # Clean up hostname to remove full FQDN
            result[0].result["neighbors"][interface][0]["hostname"] = self.clean_neighbor_name(neighbors[0]["hostname"])

            # Clean up the portname if genie incorrectly capitalized it
            result[0].result["neighbors"][interface][0]["port"] = self.clean_neighbor_port_name(neighbors[0]["port"])

    @classmethod
    def clean_neighbor_name(cls, neighbor_name):
        """Cleanup the name of a neighbor by removing all known FQDNs.

        Args:
            neighbor_name ([str]): name of a neighbor returned by cdp or lldp

        Returns:
            str: clean neighboar name
        """
        # Remove all FQDN from the hostname to match what is in the SOT
        config.SETTINGS.network.fqdns.sort(key=len, reverse=True)
        for fqdn in config.SETTINGS.network.fqdns:
            if fqdn in neighbor_name:
                return neighbor_name.replace(f".{fqdn}", "")

        return neighbor_name

    @classmethod
    def clean_neighbor_port_name(cls, port_name):
        """Work around for https://github.com/CiscoTestAutomation/genieparser/issues/287."""
        if JUNOS_INTERFACE_PATTERN.match(port_name):
            port_name = port_name[0].lower() + port_name[1:]
            return port_name

        return port_name
