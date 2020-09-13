import pdb
import logging
from collections import defaultdict

from nornir.plugins.tasks.networking import netmiko_send_command
from nornir.core.task import Result, Task
from nornir.core.exceptions import NornirSubTaskError

import network_importer.config as config
from network_importer.drivers.default import NetworkImporterDriver as DefaultNetworkImporterDriver
from network_importer.processors.get_neighbors import Neighbors, Neighbor
from network_importer.utils import is_interface_lag

from napalm.base.helpers import canonical_interface_name

logger = logging.getLogger("network-importer")


def convert_genie_lldp_details(device_name, data):
    """Convert the data returned by Genie for show lldp neighbors detail to Neighbors()

    Args:
        device_name (str): the name of the device where the data was collected
        data (Dict): the parsed data returned by Genie

    Returns:
        Neighbors: List of neighbors in a Pydantic model
    """

    results = Neighbors()

    if "interfaces" not in data:
        return results

    for intf_name, intf_data in data["interfaces"].items():
        if "port_id" not in intf_data.keys():
            continue

        # intf_name = canonical_interface_name(intf_name)
        for nei_intf_name in list(intf_data["port_id"].keys()):

            # nei_intf_name_long = canonical_interface_name(nei_intf_name)
            if is_interface_lag(nei_intf_name):
                logger.debug(
                    f"{device_name} | Neighbors, {nei_intf_name} is connected to {intf_name} but is not a valid interface (lag), SKIPPING  "
                )
                continue

            if "neighbors" not in intf_data["port_id"][nei_intf_name]:
                logger.debug(f"{device_name} | No neighbor found for {nei_intf_name} connected to {intf_name}")
                continue

            if len(intf_data["port_id"][nei_intf_name]["neighbors"]) > 1:
                logger.warning(
                    f"{device_name} | More than 1 neighbor found for {nei_intf_name} connected to {intf_name}, SKIPPING"
                )
                continue

            neighbor = Neighbor(
                hostname=list(intf_data["port_id"][nei_intf_name]["neighbors"].keys())[0], port=nei_intf_name
            )

            results.neighbors[intf_name].append(neighbor)

    return results


class NetworkImporterDriver(DefaultNetworkImporterDriver):
    @staticmethod
    def get_config(task: Task) -> Result:
        """Get the latest configuration from the device using Netmiko 

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        logger.debug(f"Executing get_config for {task.host.name} ({task.host.platform})")

        try:
            result = task.run(task=netmiko_send_command, command_string="show run")
        except NornirSubTaskError as e:

            # if isinstance(e.exception, SomeException):
            #     # handle exception
            # elif isinstance(e.exception, SomeOtherException):
            #     # handle exception
            # else:
            # raise e  # I don't know how to handle this
            logger.debug(f"An exception occured while pulling the configuration ({e.exception})")
            return Result(host=task.host, failed=True)

        if result[0].failed:
            return result

        running_config = result[0].result
        return Result(host=task.host, result={"config": running_config})

    @staticmethod
    def get_neighbors(task: Task) -> Result:
        logger.debug(f"Executing get_neighbor for {task.host.name} ({task.host.platform})")

        if config.main["import_cabling"] == "lldp":
            command = "show lldp neighbors detail"
            cmd_type = "LLDP"
        elif config.main["import_cabling"] == "cdp":
            command = "show cdp neighbors detail"
            cmd_type = "CDP"
        else:
            return Result(host=task.host, failed=True)

        try:
            result = task.run(task=netmiko_send_command, command_string="show lldp neighbors detail", use_genie=True)
        except NornirSubTaskError as e:
            logger.debug(f"An exception occured while pulling {cmd_type} data")
            return Result(host=task.host, failed=True)

        if result[0].failed:
            return result

        results = convert_genie_lldp_details(device_name=task.host.name, data=result[0].result)
        return Result(host=task.host, result=results.dict())
