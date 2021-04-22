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

# from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task

import network_importer.config as config

LOGGER = logging.getLogger("network-importer")


def dispatcher(task: Task, method: str) -> Result:
    """Helper Task to retrieve a given Nornir task for a given platform
    Args:
        task (Nornir Task):  Nornir Task object
        task (Nornir Task):  Nornir Task object
    Returns:
        Result: Nornir Task result
    """

    LOGGER.debug("Executing dispatcher for %s (%s)", task.host.name, task.host.platform)

    # Get the platform specific driver, if not available, get the default driver
    driver = config.SETTINGS.drivers.mapping.get(task.host.platform, config.SETTINGS.drivers.mapping.get("default"))
    LOGGER.debug("Found driver %s", driver)

    if not driver:
        LOGGER.warning(
            "%s | Unable to find the driver for %s for platform : %s", task.host.name, method, task.host.platform
        )
        return Result(host=task.host, failed=True)

    driver_class = getattr(importlib.import_module(driver), "NetworkImporterDriver")

    if not driver_class:
        LOGGER.error("%s | Unable to locate the class %s", task.host.name, driver)
        return Result(host=task.host, failed=True)

    try:
        driver_task = getattr(driver_class, method)
    except AttributeError:
        LOGGER.error("%s | Unable to locate the method %s for %s", task.host.name, method, driver)
        return Result(host=task.host, failed=True)

    result = task.run(task=driver_task)

    return Result(host=task.host, result=result)
