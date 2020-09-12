import pdb
import logging
from collections import defaultdict

from nornir.plugins.tasks.networking import netmiko_send_command
from nornir.core.task import Result, Task
from nornir.core.exceptions import NornirSubTaskError

import network_importer.config as config
from network_importer.drivers.default import NetworkImporterDriver as DefaultNetworkImporterDriver

logger = logging.getLogger("network-importer")


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

            try:
                result = task.run(task=netmiko_send_command, command_string="show lldp neighbors", use_textfsm=True)
            except NornirSubTaskError as e:
                pdb.set_trace()
                logger.debug(f"An exception occured while pulling lldp_data")
                return Result(host=task.host, failed=True)

            if result[0].failed:
                return result

            print(result[0].result)
            # pdb.set_trace()
            [
                {
                    "neighbor": "er02.atl01.riotdirec",
                    "local_interface": "HundredGigE0/0/0/0",
                    "neighbor_interface": "HundredGigE0/0/0/0",
                },
                {
                    "neighbor": "er02.atl01.riotdirec",
                    "local_interface": "HundredGigE0/0/0/0",
                    "neighbor_interface": "Bundle-Ether1",
                },
                {
                    "neighbor": "er02.atl01.riotdirec",
                    "local_interface": "HundredGigE0/0/0/1",
                    "neighbor_interface": "HundredGigE0/0/0/1",
                },
                {"neighbor": "ms01.atl01", "local_interface": "TenGigE0/0/0/35/3", "neighbor_interface": "xe-0/1/0"},
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/33/3",
                    "neighbor_interface": "f8f2.1e89.71e0",
                },
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/33/2",
                    "neighbor_interface": "e443.4bbf.8796",
                },
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/33/1",
                    "neighbor_interface": "f8f2.1e89.7860",
                },
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/33/0",
                    "neighbor_interface": "e443.4bbc.8998",
                },
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/32/1",
                    "neighbor_interface": "e443.4b74.b620",
                },
                {
                    "neighbor": "er02.chi01.riotdirec",
                    "local_interface": "TenGigE0/0/0/31/0",
                    "neighbor_interface": "TenGigE0/0/0/18/0",
                },
                {"neighbor": "ma01.atl01", "local_interface": "TenGigE0/0/0/30/2", "neighbor_interface": "ethernet4"},
                {"neighbor": "ma01.atl01", "local_interface": "TenGigE0/0/0/30/1", "neighbor_interface": "ethernet2"},
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/29/3",
                    "neighbor_interface": "e443.4b74.b622",
                },
                {"neighbor": "br01.mia01", "local_interface": "TenGigE0/0/0/29/2", "neighbor_interface": "xe-1/0/0"},
                {"neighbor": "ms02.atl01", "local_interface": "TenGigE0/0/0/29/1", "neighbor_interface": "xe-0/1/0"},
                {
                    "neighbor": "er02.chi01.riotdirec",
                    "local_interface": "TenGigE0/0/0/28/1",
                    "neighbor_interface": "TenGigE0/0/0/16/0",
                },
                {"neighbor": "ma01.atl01", "local_interface": "TenGigE0/0/0/27/3", "neighbor_interface": "ethernet8"},
                {
                    "neighbor": "er02.chi01.riotdirec",
                    "local_interface": "TenGigE0/0/0/27/1",
                    "neighbor_interface": "Bundle-Ether13",
                },
                {
                    "neighbor": "er02.chi01.riotdirec",
                    "local_interface": "TenGigE0/0/0/27/1",
                    "neighbor_interface": "TenGigE0/0/0/17/0",
                },
                {"neighbor": "ma01.atl01", "local_interface": "TenGigE0/0/0/27/0", "neighbor_interface": "ethernet7"},
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/25/3",
                    "neighbor_interface": "f8f2.1e89.71e1",
                },
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/25/2",
                    "neighbor_interface": "e443.4bbf.8798",
                },
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/25/1",
                    "neighbor_interface": "f8f2.1e89.7861",
                },
                {
                    "neighbor": "[DISABLED]",
                    "local_interface": "TenGigE0/0/0/25/0",
                    "neighbor_interface": "e443.4bbc.899a",
                },
            ]

            # neighbors = result[0].result.get("lldp_neighbors", {})
            return Result(host=task.host, result={"neighbors": {}})

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
