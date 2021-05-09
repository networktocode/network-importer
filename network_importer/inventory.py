"""Norning Inventory for netbox.

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
# Disable too-many-arguments and too-many-locals pylint tests for this file. These are both necessary
# pylint: disable=R0913,R0914,E1101,W0613

import copy
from typing import Any, Dict, List, Optional, Union, List

# from nornir.core.deserializer.inventory import Inventory, HostsDict
from nornir.core.inventory import Defaults, Group, Groups, Host, Hosts, Inventory, ParentGroups
from nornir.core.plugins.inventory import InventoryPluginRegister


class NetworkImporterHost(Host):
    """Network Importer Host Class."""

    site_name: Optional[str]
    """Name of the site this device belong to."""

    is_reacheable: Optional[bool]
    """Global Flag to indicate if we are able to connect to a device"""

    status: Optional[str] = "ok"
    """ Valid Statuses
        ok: device is reachable
        fail-ip: Primary IP address not reachable
        fail-access: Unable to access the device management. 
                     The IP is reachable, but SSH or API is not enabled or responding.
        fail-login: Unable to login authenticate with device
        fail-other:  Other general processing error (also catches traps/bug)
    """

    has_config: Optional[bool] = False
    """ Indicate if the configuration is present and has been properly imported in Batfish."""

    not_reachable_reason: Optional[str]


class NetworkImporterInventory:
    def __init__(
        self,
        username: Optional[str],
        password: Optional[str],
        enable: Optional[bool],
        supported_platforms: Optional[List[str]],
        limit: Optional[str],
        params: Optional[Dict] = None,
    ):
        pass


# -----------------------------------------------------------------
# Inventory Filter functions
# -----------------------------------------------------------------
def valid_devs(host):
    """Inventory Filter for Nornir for all valid devices.

    Return True or False if a device is valid

    Args:
      host(Host): Nornir Host

    Returns:
        bool: True if the device has a config, False otherwise.
    """
    if host.has_config:
        return True

    return False


def non_valid_devs(host):
    """Inventory Filter for Nornir for all non-valid devices.

    Return True or False if a device is not valid

    Args:
      host(Host): Nornir Host

    Returns:
        bool: True if the device do not have a config, False otherwise.
    """
    if host.has_config:
        return False

    return True


def reachable_devs(host):
    """Inventory Filter for Nornir for all reachable devices.

    Return True if the device is reachable.

    Args:
      host(Host): Nornir Host

    Returns:
        bool: True if the device is reachable, False otherwise.
    """
    if host.is_reachable:
        return True

    return False


def non_reachable_devs(host):
    """Inventory Filter for Nornir for all non reachable devices.

    Return True if the device is not reachable.

    Args:
      host(Host): Nornir Host

    Returns:
        bool: True if the device is not reachable, False otherwise.
    """
    if host.is_reachable:
        return False

    return True


def valid_and_reachable_devs(host):
    """Inventory Filter for Nornir for all valid and reachable devices.

    Return True if the device is reachable and has a config.

    Args:
      host(Host): Nornir Host

    Returns:
        bool: True if the device is reachable and has a config, False otherwise.
    """
    if host.is_reachable and host.has_config:
        return True

    return False
