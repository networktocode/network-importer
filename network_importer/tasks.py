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

import network_importer
import network_importer.config as config

from network_importer.model import (
    NetworkImporterDevice,
    NetworkImporterInterface,
    NetworkImporterSite,
    NetworkImporterVlan,
)

logger = logging.getLogger("network-importer")

def initialize_devices(task):
    """

    """

    nb = pynetbox.api(config.netbox.get("address"), token=config.netbox.get("token"))

    # TODO add check to ensure device is present
    # Also only pull the cache if the object exist already
    nb_dev = nb.dcim.devices.get(name=task.host.name)

    dev = NetworkImporterDevice(
        name=task.host.name, nb=nb, pull_cache=True
    )

    logger.info(f"Initializing Device {dev.name} .. ")

    if nb_dev:
        dev.remote = nb_dev
        dev.exist_remote = True

    return dev



def device_generate_hostvars(task):
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


def collect_vlans_info(task):
    """
    Collect Vlans information on all devices
    Supported Devices:
        Cisco IOS/IOS_XE >> Genie
        Cisco NX-OS >> Genie

    """
    results = task.run(task=netmiko_send_command, command_string="show vlan", use_genie=True)

    # TODO check if task went well
    vlans = results[0].results

    return vlans


def collect_lldp_neighbors(task):
    """
    Collect Vlans information on all devices
    Supported Devices:
        TODO
    """

    ## TODO Check if device is if the right type
    ## TODO check if all information are available to connect
    ## TODO Check if reacheable
    ## TODO Manage exception
    results = task.run(task=netmiko_send_command, command_string="show lldp neighbors", use_genie=True)

    # TODO check if task went well
    vlans = results[0].results

    return vlans




