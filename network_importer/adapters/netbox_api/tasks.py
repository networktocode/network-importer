"""Collection of nornir tasks for the NetboxAPIAdapter.

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

import pynetbox
import requests
from nornir.core.task import Result, Task

import network_importer.config as config  # pylint: disable=import-error

LOGGER = logging.getLogger("network-importer")


def query_device_info_from_netbox(task: Task) -> Result:
    """Nornir Task to query the device information from NetBox.

    Currently this task will pull both the device information but th goal is to pull additional information
    and return everything in a single dict
    TODO add logic to pull interfaces as well
    TODO add logic to pull ip addresses as well

    Args:
        task (Task): Nornir Task with a valid network device

    Returns:
        Result: Nornir Result object with the result in a dict format
    """
    netbox = pynetbox.api(url=config.SETTINGS.netbox.address, token=config.SETTINGS.netbox.token)

    if not config.SETTINGS.netbox.verify_ssl:
        session = requests.Session()
        session.verify = False
        netbox.http_session = session

    results = {
        "device": None,
        "interfaces": None,
    }

    device = netbox.dcim.devices.filter(name=task.host.name)

    if len(device) > 1:
        LOGGER.warning("More than 1 device returned from Netbox for %s", task.host.name)
        return Result(host=task.host, failed=True)

    if not device:
        LOGGER.warning("No device returned from Netbox for %s", task.host.name)
        return Result(host=task.host, failed=True)

    results["device"] = dict(device[0])

    # TODO move the logic to pull the interface and potentially IP here
    # interfaces = netbox.dcim.interfaces.filter(device=task.host.name)
    # results["interfaces"] = [ dict(intf) for intf in interfaces ]

    return Result(host=task.host, result=results)
