"""Collection of nornir tasks for the NetboxAPIAdapter."""
import logging

import pynautobot
from nornir.core.task import Result, Task

import network_importer.config as config  # pylint: disable=import-error
from network_importer.adapters.nautobot_api.settings import InventorySettings

LOGGER = logging.getLogger("network-importer")


def query_device_info_from_nautobot(task: Task) -> Result:
    """Nornir Task to query the device information from Nautobot.

    Currently this task will pull both the device information but th goal is to pull additional information
    and return everything in a single dict
    TODO add logic to pull interfaces as well
    TODO add logic to pull ip addresses as well

    Args:
        task (Task): Nornir Task with a valid network device

    Returns:
        Result: Nornir Result object with the result in a dict format
    """
    inventory_settings = InventorySettings(**config.SETTINGS.inventory.settings)
    nautobot = pynautobot.api(url=inventory_settings.address, token=inventory_settings.token)

    # Check for SSL Verification, set it to false if not. Else set to true
    if not inventory_settings.verify_ssl:
        # No manual session is required for this, pynautobot will automatically create one
        nautobot.http_session.verify = False
    else:
        nautobot.http_session.verify = True

    # Set a Results dictionary
    results = {
        "device": None,
        "interfaces": None,
    }

    # Get the device based on the filter
    device = nautobot.dcim.devices.filter(name=task.host.name)

    # Return a failed that there were too many devices returned in the filterset
    if len(device) > 1:
        LOGGER.warning("More than 1 device returned from Nautobot for %s", task.host.name)
        return Result(host=task.host, failed=True)

    # Return a failed when no devices were returned
    if not device:
        LOGGER.warning("No device returned from Nautobot for %s", task.host.name)
        return Result(host=task.host, failed=True)

    results["device"] = dict(device[0])

    # TODO move the logic to pull the interface and potentially IP here
    # interfaces = netbox.dcim.interfaces.filter(device=task.host.name)
    # results["interfaces"] = [ dict(intf) for intf in interfaces ]
    return Result(host=task.host, result=results)
