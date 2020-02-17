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
# Disable too-many-arguments and too-many-locals pylint tests for this file. These are both necessary
# pylint: disable=R0913,R0914,E1101,W0613

import os
import copy
from typing import Any, Dict, List, Optional, Union
import pynetbox

from nornir.core.deserializer.inventory import Inventory, HostsDict
import network_importer.config as config
from network_importer.model import NetworkImporterDevice


### ------------------------------------------------------------
### Network Importer Base Dict for device data
###   status:
###     ok: device is reacheable
###     fail-ip: Primary IP address not reachable
###     fail-access: Unable to access the device management. The IP is reachable, but SSH or API is not enabled or
###                  responding.
###     fail-login: Unable to login authenticate with device
###     fail-other:  Other general processing error (also catches traps/bug)
###   is_reacheable: Global Flag to indicate if we are able to connect to a device
###   has_config: Indicate if the configuration is present and has been properly imported in Batfish
### ------------------------------------------------------------

BASE_DATA = {"is_reacheable": None, "status": "ok", "has_config": False, "obj": None}

### ------------------------------------------------------------
### Inventory Classes
### ------------------------------------------------------------
class NornirInventoryFromBatfish(Inventory):
    """Construct a inventory object for Nornir based on the a list NodesProperties from Batfish"""

    def __init__(self, devices, **kwargs: Any) -> None:
        """


        Args:
          devices:
          **kwargs: Any:

        Returns:

        """

        hosts = {}
        for dev in devices.itertuples():

            host: HostsDict = {"data": copy.deepcopy(BASE_DATA)}
            host["hostname"] = dev.Hostname
            # host["data"]["vendor"] = str(dev.Vendor_Family).lower()
            host["data"]["type"] = str(dev.Device_Type).lower()

            hosts[dev.Hostname] = host

        super().__init__(hosts=hosts, groups={}, defaults={}, **kwargs)


class NBInventory(Inventory):
    """
    Netbox Inventory Class
    """

    # pylint: disable=C0330
    def __init__(
        self,
        nb_url: Optional[str] = None,
        nb_token: Optional[str] = None,
        use_slugs: bool = True,
        ssl_verify: Union[bool, str] = True,
        flatten_custom_fields: bool = True,
        filter_parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Netbox plugin
          hard copy from https://github.com/nornir-automation/nornir/blob/develop/nornir/plugins/inventory/netbox.py,
          need to see how to contribute back some of these modifications

        Args:
          nb_url: Netbox url
          You: can also use env variable NB_URL
          nb_token: Netbokx token
          use_slugs: Whether to use slugs or not
          ssl_verify: Enable
          flatten_custom_fields: Whether to assign custom fields directly to the host or not
          filter_parameters: Key
          nb_url: Optional[str]:  (Default value = None)
          nb_token: Optional[str]:  (Default value = None)
          use_slugs: bool:  (Default value = True)
          ssl_verify: (Default value = True)
          flatten_custom_fields: bool:  (Default value = True)
          filter_parameters: Optional[Dict[str: Any]]:  (Default value = None)
          **kwargs: Any:

        Returns:

        """
        filter_parameters = filter_parameters or {}
        nb_url = nb_url or os.environ.get("NB_URL", "http://localhost:8080")
        nb_token = nb_token or os.environ.get(
            "NB_TOKEN", "0123456789abcdef0123456789abcdef01234567"
        )

        nb_session = pynetbox.api(url=nb_url, ssl_verify=ssl_verify, token=nb_token)

        # fetch devices from netbox
        nb_devices: List[pynetbox.modules.dcim.Devices] = nb_session.dcim.devices.all()

        hosts = {}
        groups = {"global": {}}

        # Pull the login and password from the NI config object if available
        if "login" in config.network and config.network["login"]:
            groups["global"]["username"] = config.network["login"]

        if "password" in config.network and config.network["password"]:
            groups["global"]["password"] = config.network["password"]

        for dev in nb_devices:
            host: HostsDict = {"data": copy.deepcopy(BASE_DATA)}

            # Add value for IP address
            if dev.primary_ip:
                host["hostname"] = dev.primary_ip.address.split("/")[0]
            else:
                host["data"]["is_reacheable"] = False
                host["data"][
                    "not_reacheable_raison"
                ] = f"primary ip not defined in Netbox"

            # Add values that don't have an option for 'slug'
            host["data"]["serial"] = dev.serial
            host["data"]["vendor"] = dev.device_type.manufacturer.slug
            host["data"]["asset_tag"] = dev.asset_tag

            if flatten_custom_fields:
                for cust_field, value in dev.custom_fields.items():
                    host["data"][cust_field] = value
            else:
                host["data"]["custom_fields"] = dev.custom_fields

            # Add values that do have an option for 'slug'
            host["data"]["site"] = dev.site.slug
            host["data"]["role"] = dev.device_role.slug
            host["data"]["model"] = dev.device_type.slug

            # Attempt to add 'platform' based of value in 'slug'
            host["platform"] = dev.platform.slug if dev.platform else None

            #     "cisco_" + d["platform"]["slug"] if d["platform"] else None
            # )

            host["groups"] = ["global", dev.site.slug, dev.device_role.slug]

            if dev.site.slug not in groups.keys():
                groups[dev.site.slug] = {}

            if dev.device_role.slug not in groups.keys():
                groups[dev.device_role.slug] = {}

            host["data"]["obj"] = NetworkImporterDevice(
                dev.name,
                platform=host["platform"],
                role=host["data"]["role"],
                vendor=host["data"]["vendor"],
            )

            if (
                "hostname" in host
                and host["hostname"]
                and "platform" in host
                and host["platform"]
            ):
                host["data"]["is_reacheable"] = True

            # Assign temporary dict to outer dict
            # Netbox allows devices to be unnamed, but the Nornir model does not allow this
            # If a device is unnamed we will set the name to the id of the device in netbox
            hosts[dev.name or dev.id] = host

        # Pass the data back to the parent class
        super().__init__(hosts=hosts, groups=groups, defaults={}, **kwargs)


class StaticInventory(Inventory):
    """
    Static Inventory Class
    """

    def __init__(self, hosts: List[Dict], **kwargs: Any,) -> None:
        """
        Static Inventory for NetworkImporter
        Takes a list of hosts as input and return a NetworkImporter Inventory

        hosts = [
            {
                "name": "device1",
                "platform": "eos",
                "ip_address": "10.10.10.1"
            }
        ]

        """

        hosts = {}
        groups = {"global": {}}

        for host_ in hosts:

            host: HostsDict = {"data": copy.deepcopy(BASE_DATA)}
            host["data"]["is_reacheable"] = True

            host["hostname"] = host_["ip_address"]
            host["platform"] = host_["platform"]
            host["groups"] = ["global"]

            host["data"]["obj"] = NetworkImporterDevice(
                host_["name"], platform=host["platform"],
            )

            hosts[host_["name"]] = host

        # Pull the login and password from the NI config object if available
        if "login" in config.network and config.network["login"]:
            groups["global"]["username"] = config.network["login"]

        if "password" in config.network and config.network["password"]:
            groups["global"]["password"] = config.network["password"]

        # Pass the data back to the parent class
        super().__init__(hosts=hosts, groups=groups, defaults={}, **kwargs)


### -----------------------------------------------------------------
### Inventory Filter functions
### -----------------------------------------------------------------
def valid_devs(host):
    """


    Args:
      host:

    Returns:

    """
    if host.data["has_config"]:
        return True

    return False


def non_valid_devs(host):
    """


    Args:
      host:

    Returns:

    """
    if host.data["has_config"]:
        return False

    return True


def reacheable_devs(host):
    """


    Args:
      host:

    Returns:

    """
    if host.data["is_reacheable"]:
        return True

    return False


def non_reacheable_devs(host):
    """


    Args:
      host:

    Returns:

    """
    if host.data["is_reacheable"]:
        return False

    return True


def valid_and_reacheable_devs(host):
    """


    Args:
      host:

    Returns:

    """
    if host.data["is_reacheable"] and host.data["has_config"]:
        return True

    return False
