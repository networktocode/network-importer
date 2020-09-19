from collections import defaultdict
import logging

from typing import Dict, List

from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Task
from pydantic import BaseModel  # pylint: disable=no-name-in-module

import network_importer.config as config
from network_importer.processors import BaseProcessor

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

            # Clean up hostname to remove full FQDN
            result[0].result["neighbors"][interface][0]["hostname"] = self.clean_neighbor_name(neighbors[0]["hostname"])

    @classmethod
    def clean_neighbor_name(cls, neighbor_name):
        if config.SETTINGS.main.fqdn and config.SETTINGS.main.fqdn in neighbor_name:
            return neighbor_name.replace(f".{config.SETTINGS.main.fqdn}", "")

        return neighbor_name


# def collect_lldp_neighbors(task: Task, update_cache=True, use_cache=False) -> Result:
#     """
#     Collect LLDP neighbor information on all devices

#     Args:
#       task: Task:
#       update_cache: (Default value = True)
#       use_cache: (Default value = False)

#     """

#     cache_name = "lldp_neighbors"

#     check_data_dir(task.host.name)

#     if use_cache:
#         data = get_data_from_file(task.host.name, cache_name)
#         return Result(host=task.host, result=data)

#     neighbors = {}

#     if config.SETTINGS.main.import_cabling == "lldp":
#         try:
#             results = task.run(task=napalm_get, getters=["lldp_neighbors"])
#             neighbors = results[0].result
#         except:
#             LOGGER.debug("An exception occured while pulling lldp_data", exc_info=True)
#             return Result(host=task.host, failed=True)

#     elif config.SETTINGS.main.import_cabling == "cdp":
#         try:
#             results = task.run(task=netmiko_send_command, command_string="show cdp neighbors detail", use_textfsm=True,)

#             neighbors = {"lldp_neighbors": defaultdict(list)}

#         except:
#             LOGGER.debug("An exception occured while pulling cdp_data", exc_info=True)
#             return Result(host=task.host, failed=True)

#         # Convert CDP details output to Napalm LLDP format
#         if not isinstance(results[0].result, list):
#             LOGGER.warning(f"{task.host.name} | No CDP information returned")
#         else:
#             for neighbor in results[0].result:
#                 neighbor_hostname = neighbor.get("destination_host") or neighbor.get("dest_host")
#                 neighbor_port = neighbor["remote_port"]

#                 neighbors["lldp_neighbors"][neighbor["local_port"]].append(
#                     dict(hostname=neighbor_hostname, port=neighbor_port,)
#                 )

#     if update_cache:
#         save_data_to_file(task.host.name, cache_name, neighbors)

#     return Result(host=task.host, result=neighbors)
