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
import importlib
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import AggregatedResult, MultiResult, Result, Task

import network_importer.config as config

logger = logging.getLogger("network-importer")

# TODO Need to move this table in to the config file
DRIVERS_MAPPING = {
    # "juniper_junos": "network_importer.drivers.juniper_junos",
    "cisco_xr": "network_importer.drivers.cisco_default",
    "default": "network_importer.drivers.default",
}


def dispatcher(task: Task, method: str) -> Result:
    """Helper Task to retrieve a given Nornir task for a given platform 
    Args:
        task (Nornir Task):  Nornir Task object
        task (Nornir Task):  Nornir Task object
    Returns:
        Result: Nornir Task result
    """

    logger.debug(f"Executing dispatcher for {task.host.name} ({task.host.platform})")

    # Get the platform specific driver, if not available, get the default driver
    driver = DRIVERS_MAPPING.get(task.host.platform, DRIVERS_MAPPING.get("default"))
    logger.debug(f"Found driver {driver}")

    if not driver:
        logger.warning(f"{task.host.name} | Unable to find the driver for {method} for platform : {task.host.platform}")
        return Result(host=task.host, failed=True)

    driver_class = getattr(importlib.import_module(driver), "NetworkImporterDriver")

    if not driver_class:
        logger.error(f"{task.host.name} | Unable to locate the class {driver}")
        return Result(host=task.host, failed=True)

    try:
        driver_task = getattr(driver_class, method)
    except AttributeError:
        logger.error(f"{task.host.name} | Unable to locate the method {method} for {driver}")
        return Result(host=task.host, failed=True)

    result = task.run(task=driver_task)

    return Result(host=task.host, result=result)
