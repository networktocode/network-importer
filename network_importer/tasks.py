"""
(c) 2019 Network To Code

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

import sys
import logging
import os
import hashlib
import copy
import json
from pathlib import Path

import pynetbox

from nornir.core.task import Result, Task
from nornir.plugins.tasks.networking import netmiko_send_command, tcp_ping, napalm_get

from napalm.base.helpers import canonical_interface_name

import network_importer
import network_importer.config as config

from network_importer.model import (  # pylint: disable=W0611
    NetworkImporterDevice,
    NetworkImporterInterface,
    NetworkImporterSite,
    NetworkImporterVlan,
)


logger = logging.getLogger("network-importer")  # pylint: disable=C0103


def save_data_to_file(host, filename, content):
    """


    Args:
      host:
      filename:
      content:

    Returns:

    """

    directory = config.main["data_directory"]
    filepath = f"{directory}/{host}/{filename}.json"

    with open(filepath, "w") as file_:
        json.dump(content, file_, indent=4, sort_keys=True)

    return True


def get_data_from_file(host, filename):
    """


    Args:
      host:
      filename:

    Returns:

    """

    directory = config.main["data_directory"]
    filepath = f"{directory}/{host}/{filename}.json"

    if not os.path.exists(filepath):
        logger.debug(f"{host} | cache not available for {filename} ")
        return False

    try:
        with open(filepath) as file_:
            data = json.load(file_)
    except:
        logger.warning(f"{host} | Unable to load the cache for {filename} ")
        return False

    return data


def check_data_dir(host):
    """


    Args:
      host:

    Returns:

    """

    directory = config.main["data_directory"]
    host_dir = f"{directory}/{host}"

    if not os.path.isdir(host_dir):
        os.mkdir(host_dir)

    return True


def initialize_devices(task: Task, bfs=None) -> Result:
    """


    Args:
      task: Task:
      bfs: (Default value = None)
      task: Task:
      task: Task:

    Returns:

    """

    pynb = pynetbox.api(
        config.netbox["address"],
        token=config.netbox["token"],
        ssl_verify=config.netbox["request_ssl_verify"],
    )

    # TODO add check to ensure device is present
    # Also only pull the cache if the object exist already
    nb_dev = pynb.dcim.devices.get(name=task.host.name)

    logger.info(f"{task.host.name} | Initializing Device  .. ")

    task.host.data["obj"].nb = pynb
    task.host.data["obj"].update_cache()

    if nb_dev:
        task.host.data["obj"].remote = nb_dev
        task.host.data["obj"].exist_remote = True

    if bfs:
        try:
            task.host.data["obj"].bf = (
                bfs.q.nodeProperties(nodes=task.host.name).answer().frame().loc[0, :]
            )
            task.host.data["has_config"] = True

        except:
            logger.warning(
                f"{task.host.name} | Unable to find Batfish data  ... SKIPPING"
            )

    return Result(host=task.host, result=True)


def device_update_remote(task: Task) -> Result:
    """


    Args:
      task: Task

    Returns:

    """

    res = task.host.data["obj"].update_remote()

    return Result(host=task.host, result=res)


def device_generate_hostvars(task: Task) -> Result:
    """
    Extract the facts for each device from Batfish to generate the host_vars
    Cleaning up the interfaces for now since these information are already in netbox

    Args:
      task: Task:

    Returns:

    """
    module_path = os.path.dirname(network_importer.__file__)
    template_dir = f"{module_path}/templates/"

    # # Save device variables in file
    # if not os.path.exists(f"{options.output}/{dev.name}"):
    #     os.makedirs(f"{options.output}/{dev.name}")
    #     logger.debug(
    #         f"Directory {options.output}/{dev.name} was missing, created it"
    #     )

    # dev_facts = batfish_session.extract_facts(nodes=dev.name)["nodes"][dev.name]
    # del dev_facts["Interfaces"]

    # # Load Jinja2 template
    # # env = Environment(
    # #     loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
    # # )
    # # env.filters["to_yaml_list"] = jinja_filter_toyaml_list
    # # env.filters["to_yaml_dict"] = jinja_filter_toyaml_dict
    # # template = env.get_template("hostvars.j2")
    # # hostvars_str = template.render(dev_facts)

    # with open(
    #     f"{options.output}/{dev.name}/network_importer.yaml", "w"
    # ) as out_file:
    #     out_file.write( yaml.dump(dev_facts, default_flow_style=False))
    #     # out_file.write( hostvars_str)
    #     logger.debug(
    #         f"{dev.name} - Host variables saved in {options.output}/{dev.name}/network_importer.yaml"
    #     )

    return Result(host=task.host)


def collect_vlans_info(task: Task, update_cache=True, use_cache=False) -> Result:
    """
    Collect Vlans information on all devices
    Supported Devices:
        Cisco IOS/IOS_XE >> Genie
        Cisco NX-OS >> Genie

    Args:
      task: Task:
      update_cache: (Default value = True)
      use_cache: (Default value = False)

    Returns:

    """

    check_data_dir(task.host.name)

    cache_name = "vlans"

    if use_cache:
        data = get_data_from_file(task.host.name, cache_name)
        return Result(host=task.host, result=data)

    vlans = []

    vlan_model = {
        "name": None,
        "id": None,
    }

    results = None

    if task.host.platform in ["ios", "nxos"]:
        try:
            results = task.run(
                task=netmiko_send_command, command_string="show vlan", use_genie=True
            )
        except:
            logger.debug(
                "An exception occured while pulling the vlans information",
                exc_info=True,
            )
            return Result(host=task.host, failed=True)

        if not isinstance(results[0].result, dict) or not "vlans" in results[0].result:
            logger.warning(f"{task.host.name} | No vlans information returned")
            return Result(host=task.host, result=False)

        for vid, data in results[0].result["vlans"].items():
            vlans.append(dict(name=data["name"], id=data["vlan_id"]))

    elif task.host.platform == "eos":

        nr_device = task.host.get_connection("napalm", task.nornir.config)
        eos_device = nr_device.device
        results = eos_device.run_commands(["show vlan"])

        if not isinstance(results[0], dict) or not "vlans" in results[0]:
            logger.warning(f"{task.host.name} | No vlans information returned")
            return Result(host=task.host, result=False)

        for vid, data in results[0]["vlans"].items():
            vlans.append(dict(name=data["name"], id=vid))

    else:
        return Result(host=task.host, result=False)

    if update_cache and results:
        save_data_to_file(task.host.name, cache_name, vlans)

    return Result(host=task.host, result=vlans)


def update_configuration(  # pylint: disable=C0330
    task: Task, configs_directory, config_extension="txt"
) -> Result:
    """
    Collect running configurations on all devices

    Supported Devices:
        Default: Napalm (TODO)
        Cisco: Netmiko

    Args:
      task: Task:
      configs_directory:
      config_extension: (Default value = "txt")

    Returns:

    """

    config_filename = f"{configs_directory}/{task.host.name}.{config_extension}"

    new_config = None
    current_md5 = None

    if os.path.exists(config_filename):
        current_config = Path(config_filename).read_text()
        previous_md5 = hashlib.md5(current_config.encode("utf-8")).hexdigest()

    if task.host.platform in ["nxos", "ios"]:
        try:
            results = task.run(task=netmiko_send_command, command_string="show run")
        except:
            logger.debug(
                "An exception occured while pulling the configuration", exc_info=True
            )
            return Result(host=task.host, failed=True)

        if results.failed:
            return Result(host=task.host, failed=True)

        new_config = results[0].result

    else:
        try:
            results = task.run(
                task=napalm_get, getters=["config"], retrieve="running", full=False
            )
        except:
            logger.debug(
                "An exception occured while pulling the configuration", exc_info=True
            )
            return Result(host=task.host, failed=True)

        if results.failed:
            return Result(host=task.host, failed=True)

        new_config = results[0].result["config"]["running"]

    # Currently the configuration is going to be different everytime because there is a timestamp on it
    # Will need to do some clean up
    with open(config_filename, "w") as config_:
        config_.write(new_config)

    new_md5 = hashlib.md5(new_config.encode("utf-8")).hexdigest()
    changed = False

    if current_md5 and current_md5 == new_md5:
        logger.debug(f"{task.host.name} | Latest config file already present ... ")

    else:
        logger.info(f"{task.host.name} | Configuration file updated ")
        changed = True

    return Result(host=task.host, result=True, changed=changed)


def collect_lldp_neighbors(task: Task, update_cache=True, use_cache=False) -> Result:
    """
    Collect LLDP neighbor information on all devices

    Args:
      task: Task:
      update_cache: (Default value = True)
      use_cache: (Default value = False)

    """

    cache_name = "lldp_neighbors"

    check_data_dir(task.host.name)

    if use_cache:
        data = get_data_from_file(task.host.name, cache_name)
        return Result(host=task.host, result=data)

    try:
        results = task.run(task=napalm_get, getters=["lldp_neighbors"])
    except:
        logger.debug("An exception occured while pulling lldp_data", exc_info=True)
        return Result(host=task.host, failed=True)

    if update_cache:
        save_data_to_file(task.host.name, cache_name, results[0].result)

    return Result(host=task.host, result=results[0].result)


def collect_transceivers_info(task: Task, update_cache=True, use_cache=False) -> Result:
    """
    Collect transceiver informaton on all devices

    Supported Devices:
        Cisco IOS
        cisco_nxos

    Args:
      task: Task:
      update_cache: (Default value = True)
      use_cache: (Default value = False)

    Returns:

    """
    cache_name = "transceivers"

    if use_cache:
        data = get_data_from_file(task.host.name, cache_name)
        return Result(host=task.host, result=data)

    transceivers_inventory = []

    xcvr_model = {
        "interface": None,
        "manufacturer": None,
        "serial": None,
        "part_number": None,
        "type": None,
    }

    check_data_dir(task.host.name)

    if task.host.platform == "ios":

        try:
            results = task.run(
                task=netmiko_send_command,
                command_string="show inventory",
                use_textfsm=True,
            )
        except:
            logger.debug(
                "An exception occured while pulling the inventory", exc_info=True
            )
            return Result(host=task.host, failed=True)

        inventory = results[0].result

        cmd = "show interface transceiver"
        try:
            results = task.run(
                task=netmiko_send_command, command_string=cmd, use_textfsm=True,
            )
        except:
            logger.debug(
                "An exception occured while pulling the transceiver info", exc_info=True
            )
            return Result(host=task.host, failed=True)

        transceivers = results[0].result

        if not isinstance(transceivers, list):
            logger.debug(
                f"{task.host.name}: command: {cmd} was not returned as a list, please check if the ntc-template are installed properly"  # pylint: disable=C0301
            )
            return Result(host=task.host, result=transceivers_inventory)

        transceiver_names = [t["iface"] for t in transceivers]
        full_transceiver_names = [
            canonical_interface_name(t) for t in transceiver_names
        ]

        # Check if the optic is in the inventory by matching on the interface name
        # Normalize the name of the interface before returning it
        for item in inventory:
            xcvr = copy.deepcopy(xcvr_model)

            if item.get("name", "") in transceiver_names:
                xcvr["interface"] = canonical_interface_name(item["name"])
            elif item.get("name", "") in full_transceiver_names:
                xcvr["interface"] = item["name"]
            else:
                continue

            xcvr["serial"] = item["sn"]
            xcvr["type"] = item["descr"]

            transceivers_inventory.append(xcvr)

    elif task.host.platform == "nxos":
        cmd = "show interface transceiver"
        try:
            results = task.run(
                task=netmiko_send_command, command_string=cmd, use_textfsm=True
            )
        except:
            logger.debug(
                "An exception occured while pulling the transceiver info", exc_info=True
            )
            return Result(host=task.host, failed=True)

        transceivers = results[0].result

        if not isinstance(transceivers, list):
            logger.warning(
                f"command: {cmd} was not returned as a list, please check if the ntc-template are installed properly"
            )
            return Result(host=task.host, result=transceivers_inventory)

        for tranceiver in transceivers:
            transceivers_inventory.append(tranceiver)

    elif task.host.platform == "eos":

        nr_device = task.host.get_connection("napalm", task.nornir.config)
        eos_device = nr_device.device
        results = eos_device.run_commands(["show transceiver status"])

        transceivers = results[0]["ports"]

        for name, data in transceivers.items():

            try:
                xcvr = copy.deepcopy(xcvr_model)
                xcvr["serial"] = data["serialNumber"]["state"]
                xcvr["interface"] = list(data["interfaces"].keys())[0]
                xcvr["type"] = data["mediaType"]["state"]
                xcvr["part_number"] = data["mediaType"]["state"]
            except:
                logger.warning(
                    f"Unable to extract the transceiver information for {name} : {sys.exc_info()[0]}"
                )
                continue

            transceivers_inventory.append(xcvr)

    else:
        logger.debug(
            f"{task.host.name} | collect_transceiver_info not supported yet for {task.host.platform}"
        )

    if update_cache and transceivers_inventory:
        save_data_to_file(task.host.name, cache_name, transceivers_inventory)

    return Result(host=task.host, result=transceivers_inventory)


def check_if_reacheable(task: Task) -> Result:
    """
    Check if a device is reacheable by doing a TCP ping it on port 22

    Will change the status of the variable `is_reacheable` in host.data based on the results

   Args:
      task: Nornir Task

    Returns:
      Result:

    """

    port_to_check = 22
    try:
        results = task.run(task=tcp_ping, ports=[port_to_check])
    except:
        logger.debug(
            "An exception occured while running the reachability test (tcp_ping)",
            exc_info=True,
        )
        return Result(host=task.host, failed=True)

    is_reacheable = results[0].result[port_to_check]

    if not is_reacheable:
        logger.debug(
            f"{task.host.name} | device is not reacheable on port {port_to_check}"
        )
        task.host.data["is_reacheable"] = False
        task.host.data[
            "not_reacheable_raison"
        ] = f"device not reacheable on port {port_to_check}"
        task.host.data["status"] = "fail-ip"

    return Result(host=task.host, result=is_reacheable)


def update_device_status(task: Task) -> Result:
    """

    Update the status of the device on the remote system

    Args:
      task: Nornir Task

    Returns:
      Result:

    """

    if not config.netbox["status_update"]:
        logger.debug(f"{task.host.name} | status_update disabled skipping")
        return Result(host=task.host, result=False)

    if not task.host.data["obj"].remote:
        logger.debug(f"{task.host.name} | remote not present skipping")
        return Result(host=task.host, result=False)

    new_status = None
    prev_status = task.host.data["obj"].remote.status.value

    if task.host.data["status"] == "fail-ip":
        new_status = config.netbox["status_on_unreachable"]

    elif "fail" in task.host.data["status"]:
        new_status = config.netbox["status_on_fail"]

    else:
        new_status = config.netbox["status_on_pass"]

    if new_status not in (None, prev_status):

        task.host.data["obj"].remote.update(data={"status": new_status})
        logger.info(
            f"{task.host.name} | Updated status on netbox {prev_status} > {new_status}"
        )
        return Result(host=task.host, result=True)

    logger.debug(f"{task.host.name} | no status update required")

    return Result(host=task.host, result=False)
