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

import logging
import pynetbox
import os
import hashlib
from pathlib import Path

from typing import Optional, List

import network_importer
import network_importer.config as config

from network_importer.model import (
    NetworkImporterDevice,
    NetworkImporterInterface,
    NetworkImporterSite,
    NetworkImporterVlan,
)

from nornir.core.task import Result, Task
from nornir.plugins.tasks.networking import netmiko_send_command

from napalm.base.helpers import canonical_interface_name

logger = logging.getLogger("network-importer")


def initialize_devices(task: Task, bfs=None) -> Result:
    """

    """

    nb = pynetbox.api(config.netbox.get("address"), token=config.netbox.get("token"))

    # TODO add check to ensure device is present
    # Also only pull the cache if the object exist already
    nb_dev = nb.dcim.devices.get(name=task.host.name)

    logger.info(f" {task.host.name} | Initializing Device  .. ")

    task.host.data['obj'].nb = nb
    task.host.data['obj'].update_cache()

    # dev = NetworkImporterDevice(name=task.host.name, nb=nb, pull_cache=True)

    if nb_dev:
        task.host.data['obj'].remote = nb_dev
        task.host.data['obj'].exist_remote = True

    if bfs:
        try:
            # TODO convert this action to a function to be able to properly extract
            task.host.data['obj'].bf = (
                bfs.q.nodeProperties(nodes=task.host.name).answer().frame().loc[0, :]
            )

        except:
            logger.warning(
                f"Unable to find {task.host.name} in Batfish data  ... SKIPPING"
            )

    return Result(host=task.host, result=True)

def device_update_remote(task: Task) -> Result:
    
    res = task.host.data['obj'].update_remote()

    return Result(host=task.host, result=res)

def device_generate_hostvars(task: Task) -> Result:
    """
    Extract the facts for each device from Batfish to generate the host_vars
    Cleaning up the interfaces for now since these information are already in netbox
    """
    module_path = os.path.dirname(network_importer.__file__)
    TPL_DIR = f"{module_path}/templates/"

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
    # #     loader=FileSystemLoader(TPL_DIR), trim_blocks=True, lstrip_blocks=True
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

def collect_vlans_info(task: Task) -> Result:
    """
    Collect Vlans information on all devices
    Supported Devices:
        Cisco IOS/IOS_XE >> Genie
        Cisco NX-OS >> Genie

    """
    results = task.run(
        task=netmiko_send_command, command_string="show vlan", use_genie=True
    )

    # TODO check if task went well
    return Result(host=task.host, result=results[0].result)


def update_configuration(task: Task, configs_directory, config_extension="txt") -> Result:
    """
    Collect running configurations on all devices

    Supported Devices:
        Default: Napalm (TODO)
        Cisco: Netmiko
    """

    config_filename = f"{configs_directory}/{task.host.name}.{config_extension}"

    current_md5 = None
    if os.path.exists(config_filename):
        current_config = Path(config_filename).read_text()
        previous_md5 = hashlib.md5(current_config.encode("utf-8")).hexdigest()

    results = task.run(task=netmiko_send_command, command_string="show run")

    if results.failed:
        return Result(host=task.host, failed=True)

    new_config = results[0].result

    # Currently the configuration is going to be different everytime because there is a timestamp on it
    # Will need to do some clean up
    with open(config_filename, "w") as config:
        config.write(new_config)

    new_md5 = hashlib.md5(new_config.encode("utf-8")).hexdigest()
    changed = False

    if current_md5 and current_md5 == new_md5:
        logger.debug(f" {task.host.name} | Latest config file already present ... ")

    else:
        logger.debug(f" {task.host.name} | Configuration file updated ")
        changed = True

    return Result(host=task.host, result=True, changed=changed)


def collect_lldp_neighbors(task: Task) -> Result:
    """
    Collect Vlans information on all devices
    Supported Devices:
        TODO
    """

    ## TODO Check if device is if the right type
    ## TODO check if all information are available to connect
    ## TODO Check if reacheable
    ## TODO Manage exception
    results = task.run(
        task=netmiko_send_command, command_string="show lldp neighbors", use_genie=True
    )

    # TODO check if task went well
    return Result(host=task.host, result=results[0].result)


def collect_transceivers_info(task: Task) -> Result:
    """
    Collect transceiver informaton on all devices
    """

    transceivers_inventory = []

    if task.host.platform != "cisco_ios":
        logger.warning(
            f" {task.host.name} | Collect transceiver not available for {task.host.platform} yet "
        )
        return Result(host=task.host, failed=True)

    results = task.run(
        task=netmiko_send_command, command_string="show inventory", use_textfsm=True
    )
    inventory = results[0].result

    results = task.run(
        task=netmiko_send_command,
        command_string="show interface transceiver",
        use_textfsm=True,
    )
    transceivers = results[0].result

    transceiver_names = [t["iface"] for t in transceivers]

    # Check if the optic is in the inventory by matching on the interface name
    # Normalize the name of the interface before returning it
    for item in inventory:
        if item.get("name", "") in transceiver_names:
            item["name"] = canonical_interface_name(item["name"])
            transceivers_inventory.append(item)

    return Result(host=task.host, result=transceivers_inventory)
