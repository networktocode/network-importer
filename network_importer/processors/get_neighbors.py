from collections import defaultdict
import logging

from typing import Dict, List

from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Task
from pydantic import BaseModel  # pylint: disable=no-name-in-module

import network_importer.config as config
from network_importer.processors import BaseProcessor
from network_importer.utils import is_mac_address

LOGGER = logging.getLogger("network-importer")


# TODO Create a Filter based on that
# if host.platform in config.main["excluded_platforms_cabling"]:
#     LOGGER.debug(f"{host.name}: device type ({task.host.platform}) found in excluded_platforms_cabling")
#     return


class Neighbor(BaseModel):
    hostname: str
    port: str


class Neighbors(BaseModel):
    neighbors: Dict[str, List[Neighbor]] = defaultdict(list)


class GetNeighbors(BaseProcessor):

    task_name = "get_neighbors"

    def __init__(self) -> None:
        pass

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Before getting the new configuration, check if a configuration already exist and calculate it's md5

        Args:
            task (Task): Nornir Task
            host (Host): Nornir Host
        """

        if task.name != self.task_name:
            return

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:

        if task.name != self.task_name:
            return

        if result[0].failed:
            LOGGER.warning("%s | Something went wrong while trying to pull the neighbor information", host.name)
            host.data["status"] = "fail-other"
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

    @classmethod
    def clean_neighbor_name(cls, neighbor_name):
        if config.SETTINGS.main.fqdn and config.SETTINGS.main.fqdn in neighbor_name:
            return neighbor_name.replace(f".{config.SETTINGS.main.fqdn}", "")

        return neighbor_name
