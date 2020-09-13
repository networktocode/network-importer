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
import os
import json
import yaml

from nornir.core.task import Result, Task
from nornir.plugins.tasks.networking import tcp_ping

import network_importer.config as config

logger = logging.getLogger("network-importer")  # pylint: disable=C0103


def save_data_to_file(host, filename, content):
    """Save content to a file in JSON format for a given host. 

    Args:
      host (str): Name of the host
      filename (str): Name of the output file where the data will be saved
      content (dict or list): Content to save in the file
    """

    directory = config.main["data_directory"]
    filepath = f"{directory}/{host}/{filename}.json"

    with open(filepath, "w") as file_:
        json.dump(content, file_, indent=4, sort_keys=True)


def get_data_from_file(host, filename):
    """Get data from a JSON file for a given host.

    Args:
      host (str): Name of the host
      filename (str): Name of the file to get data from

    Returns:
        bool, dict or list, depending on the content of the file
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
    """Check if a directory exist of a given host, create it if it doesn't exist.

    Args:
      host (str): Name of the host
    """

    directory = config.main["data_directory"]
    host_dir = f"{directory}/{host}"

    if not os.path.isdir(host_dir):
        os.mkdir(host_dir)


def device_save_hostvars(task: Task) -> Result:
    """
    Save the device hostvars into a yaml file

    Args:
      task (Task): Nornir Task

    Returns:
      Result
    """

    if not task.host.data["obj"].hostvars:
        return Result(host=task.host)

    # Save device hostvars in file
    if not os.path.exists(f"{config.main['hostvars_directory']}/{task.host.name}"):
        os.makedirs(f"{config.main['hostvars_directory']}/{task.host.name}")
        logger.debug(f"Directory {config.main['hostvars_directory']}/{task.host.name} was missing, created it")

    with open(f"{config.main['hostvars_directory']}/{task.host.name}/network_importer.yaml", "w",) as out_file:
        out_file.write(yaml.dump(task.host.data["obj"].hostvars, default_flow_style=False))
        logger.debug(
            f"{task.host.name} - Host variables saved in {config.main['hostvars_directory']}/{task.host.name}/network_importer.yaml"
        )

    return Result(host=task.host)

    # -------------------------------------------------------------------
    # Old code that need used previously to generate the hostvars from a jinja templates
    # -------------------------------------------------------------------
    # module_path = os.path.dirname(network_importer.__file__)
    # template_dir = f"{module_path}/templates/"

    # dev_facts = task.host.data["obj"].bf.extract_facts(nodes=task.host.name)["nodes"][task.host.name]
    # del dev_facts["Interfaces"]

    # # Load Jinja2 template
    # # env = Environment(
    # #     loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
    # # )
    # # env.filters["to_yaml_list"] = jinja_filter_toyaml_list
    # # env.filters["to_yaml_dict"] = jinja_filter_toyaml_dict
    # # template = env.get_template("hostvars.j2")
    # # hostvars_str = template.render(dev_facts)


def check_if_reachable(task: Task) -> Result:
    """
    Check if a device is reachable by doing a TCP ping it on port 22

    Will change the status of the variable `is_reachable` in host.data based on the results

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
            "An exception occured while running the reachability test (tcp_ping)", exc_info=True,
        )
        return Result(host=task.host, failed=True)

    is_reachable = results[0].result[port_to_check]

    if not is_reachable:
        logger.debug(f"{task.host.name} | device is not reachable on port {port_to_check}")
        task.host.data["is_reachable"] = False
        task.host.data["not_reachable_reason"] = f"device not reachable on port {port_to_check}"
        task.host.data["status"] = "fail-ip"

    return Result(host=task.host, result=is_reachable)


# def update_device_status(task: Task) -> Result:
#     """

#     Update the status of the device on the remote system

#     Args:
#       task: Nornir Task

#     Returns:
#       Result:

#     """

#     if not config.netbox["status_update"]:
#         logger.debug(f"{task.host.name} | status_update disabled skipping")
#         return Result(host=task.host, result=False)

#     if not task.host.data["obj"].remote:
#         logger.debug(f"{task.host.name} | remote not present skipping")
#         return Result(host=task.host, result=False)

#     new_status = None
#     prev_status = task.host.data["obj"].remote.status.value

#     if task.host.data["status"] == "fail-ip":
#         new_status = config.netbox["status_on_unreachable"]

#     elif "fail" in task.host.data["status"]:
#         new_status = config.netbox["status_on_fail"]

#     else:
#         new_status = config.netbox["status_on_pass"]

#     if new_status not in (None, prev_status):

#         task.host.data["obj"].remote.update(data={"status": new_status})
#         logger.info(f"{task.host.name} | Updated status on netbox {prev_status} > {new_status}")
#         return Result(host=task.host, result=True)

#     logger.debug(f"{task.host.name} | no status update required")

#     return Result(host=task.host, result=False)
