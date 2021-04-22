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
from typing import Any, Dict, List, Optional, Union

import requests
import pynetbox

from nornir.core.deserializer.inventory import Inventory, HostsDict

# import network_importer.config as config

# ------------------------------------------------------------
# Network Importer Base Dict for device data
#   status:
#     ok: device is reachable
#     fail-ip: Primary IP address not reachable
#     fail-access: Unable to access the device management. The IP is reachable, but SSH or API is not enabled or
#                  responding.
#     fail-login: Unable to login authenticate with device
#     fail-other:  Other general processing error (also catches traps/bug)
#   is_reachable: Global Flag to indicate if we are able to connect to a device
#   has_config: Indicate if the configuration is present and has been properly imported in Batfish
# ------------------------------------------------------------

BASE_DATA = {"is_reachable": None, "status": "ok", "has_config": False}


class NetboxInventory(Inventory):
    """Netbox Inventory Class."""

    # pylint: disable=dangerous-default-value, too-many-branches, too-many-statements
    def __init__(
        self,
        nb_url: Optional[str] = None,
        nb_token: Optional[str] = None,
        ssl_verify: Union[bool, str] = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        enable: Optional[bool] = True,
        use_primary_ip: Optional[bool] = True,
        fqdn: Optional[str] = None,
        supported_platforms: Optional[List[str]] = [],
        filter_parameters: Optional[Dict[str, Any]] = None,
        global_delay_factor: Optional[int] = 5,
        banner_timeout: Optional[int] = 15,
        conn_timeout: Optional[int] = 5,
        **kwargs: Any,
    ) -> None:
        """Norning Inventory Plugin fir Netbox.

        Hard copy from https://github.com/nornir-automation/nornir/blob/develop/nornir/plugins/inventory/netbox.py,
        Need to see how to contribute back some of these modifications

        Args:
          filter_parameters: Key
          nb_url: Optional[str]:  (Default value = None)
          nb_token: Optional[str]:  (Default value = None)
          ssl_verify: (Default value = True)
          filter_parameters: Optional[Dict[str: Any]]:  (Default value = None)
          username: Optional[str]
          password: Optional[str]
          enable: Optional[bool] = True,
          use_primary_ip: Optional[bool] = True,
          fqdn: Optional[str] = None,
          supported_platforms: Optional[List[str]]
          global_delay_factor: Optional[int] Global Delay factor for netmiko
          banner_timeout: Optional[int] Banner Timeout for netmiko/paramiko
          conn_timeout: Optional[int] Connection timeout for netmiko/paramiko
          **kwargs: Any:
        """
        filter_parameters = filter_parameters or {}

        if "exclude" not in filter_parameters.keys():
            filter_parameters["exclude"] = "config_context"

        # Instantiate netbox session using pynetbox
        nb_session = pynetbox.api(url=nb_url, token=nb_token)
        if not ssl_verify:
            session = requests.Session()
            session.verify = False
            nb_session.http_session = session

        # fetch devices from netbox
        if filter_parameters:
            nb_devices: List[pynetbox.modules.dcim.Devices] = nb_session.dcim.devices.filter(**filter_parameters)
        else:
            nb_devices: List[pynetbox.modules.dcim.Devices] = nb_session.dcim.devices.all()

        # fetch all platforms from Netbox and build mapping:   platform:  napalm_driver
        platforms = nb_session.dcim.platforms.all()
        platforms_mapping = {platform.slug: platform.napalm_driver for platform in platforms if platform.napalm_driver}

        hosts = {}
        groups = {"global": {"connection_options": {"netmiko": {"extras": {}}, "napalm": {"extras": {}}}}}

        # Pull the login and password from the NI config object if available
        if username:
            groups["global"]["username"] = username

        if password:
            groups["global"]["password"] = password
            if enable:
                groups["global"]["connection_options"]["netmiko"]["extras"] = {
                    "secret": password,
                    "global_delay_factor": global_delay_factor,
                    "banner_timeout": banner_timeout,
                    "conn_timeout": conn_timeout,
                }
                groups["global"]["connection_options"]["napalm"]["extras"] = {"optional_args": {"secret": password}}

        for dev in nb_devices:

            host: HostsDict = {"data": copy.deepcopy(BASE_DATA)}

            # Only add virtual chassis master as inventory element
            if dev.virtual_chassis and dev.virtual_chassis.master:
                if dev.id != dev.virtual_chassis.master.id:
                    continue
                host["data"]["virtual_chassis"] = True

            else:
                host["data"]["virtual_chassis"] = False

            # If supported_platforms is provided
            # skip all devices that do not match the list of supported platforms
            # TODO need to see if we can filter when doing the query directly
            if supported_platforms:
                if not dev.platform:
                    continue

                if dev.platform.slug not in supported_platforms:
                    continue

            # Add value for IP address
            if use_primary_ip and dev.primary_ip:
                host["hostname"] = dev.primary_ip.address.split("/")[0]
            elif use_primary_ip and not dev.primary_ip:
                host["data"]["is_reachable"] = False
                host["data"]["not_reachable_reason"] = "primary ip not defined in Netbox"
            elif not use_primary_ip and fqdn:
                host["hostname"] = f"{dev.name}.{fqdn}"
            elif not use_primary_ip:
                host["hostname"] = dev.name

            host["data"]["serial"] = dev.serial
            host["data"]["vendor"] = dev.device_type.manufacturer.slug
            host["data"]["asset_tag"] = dev.asset_tag
            host["data"]["custom_fields"] = dev.custom_fields
            host["data"]["site"] = dev.site.slug
            host["data"]["site_id"] = dev.site.id
            host["data"]["device_id"] = dev.id
            host["data"]["role"] = dev.device_role.slug
            host["data"]["model"] = dev.device_type.slug

            # Attempt to add 'platform' based of value in 'slug'
            if dev.platform and dev.platform.slug in platforms_mapping:
                host["connection_options"] = {"napalm": {"platform": platforms_mapping[dev.platform.slug]}}

            if dev.platform:
                host["platform"] = dev.platform.slug
            else:
                host["platform"] = None

            host["groups"] = ["global", dev.site.slug, dev.device_role.slug]

            if dev.site.slug not in groups.keys():
                groups[dev.site.slug] = {}

            if dev.device_role.slug not in groups.keys():
                groups[dev.device_role.slug] = {}

            if "hostname" in host and host["hostname"] and "platform" in host and host["platform"]:
                host["data"]["is_reachable"] = True

            # Assign temporary dict to outer dict
            # Netbox allows devices to be unnamed, but the Nornir model does not allow this
            # If a device is unnamed we will set the name to the id of the device in netbox
            hosts[dev.name or dev.id] = host

        # Pass the data back to the parent class
        super().__init__(hosts=hosts, groups=groups, defaults={}, **kwargs)


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
    if host.data["has_config"]:
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
    if host.data["has_config"]:
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
    if host.data["is_reachable"]:
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
    if host.data["is_reachable"]:
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
    if host.data["is_reachable"] and host.data["has_config"]:
        return True

    return False
