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

from nornir.core.deserializer.inventory import Inventory, HostsDict

import os
import requests
from typing import Any, Dict, List, Optional, Union
import network_importer.config as config
from network_importer.model import NetworkImporterDevice


### ------------------------------------------------------------
### Network Importer Base Dict for device data
###   status:
###     ok: device is reacheable
###     fail-ip: Primary IP address not reachable
###     fail-access: Unable to access the device management. The IP is reachable, but SSH or API is not enabled or responding.
###     fail-login: Unable to login authenticate with device
###     fail-other:  Other general processing error (also catches traps/bug)
###   is_reacheable: Global Flag to indicate if we are able to connect to a device
###   has_config: Indicate if the configuration is present and has been properly imported in Batfish
### ------------------------------------------------------------

base_data = {"is_reacheable": None, "status": "ok", "has_config": False, "obj": None}

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

            host: HostsDict = {"data": copy.deepcopy(base_data)}
            host["hostname"] = dev.Hostname
            # host["data"]["vendor"] = str(dev.Vendor_Family).lower()
            host["data"]["type"] = str(dev.Device_Type).lower()

            hosts[dev.Hostname] = host

        super().__init__(hosts=hosts, groups={}, defaults={}, **kwargs)


class NBInventory(Inventory):
    """ """

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

        session = requests.Session()
        session.headers.update({"Authorization": f"Token {nb_token}"})
        session.verify = ssl_verify

        # Fetch all devices from Netbox
        # Since the api uses pagination we have to fetch until no next is provided

        url = f"{nb_url}/api/dcim/devices/?limit=0"
        nb_devices: List[Dict[str, Any]] = []

        while url:
            r = session.get(url, params=filter_parameters)

            if not r.status_code == 200:
                raise ValueError(f"Failed to get devices from Netbox instance {nb_url}")

            resp = r.json()
            nb_devices.extend(resp.get("results"))

            url = resp.get("next")

        hosts = {}
        groups = {"global": {}}

        # Pull the login and password from the NI config object if available
        if "login" in config.network and config.network["login"]:
            groups["global"]["username"] = config.network["login"]

        if "password" in config.network and config.network["password"]:
            groups["global"]["password"] = config.network["password"]

        for d in nb_devices:
            host: HostsDict = {"data": copy.deepcopy(base_data)}

            # Add value for IP address
            if d.get("primary_ip", {}):
                host["hostname"] = d["primary_ip"]["address"].split("/")[0]
            else:
                host["data"]["is_reacheable"] = False
                host["data"][
                    "not_reacheable_raison"
                ] = f"primary ip not defined in Netbox"

            # Add values that don't have an option for 'slug'
            host["data"]["serial"] = d["serial"]
            host["data"]["vendor"] = d["device_type"]["manufacturer"]["slug"]
            host["data"]["asset_tag"] = d["asset_tag"]

            if flatten_custom_fields:
                for cf, value in d["custom_fields"].items():
                    host["data"][cf] = value
            else:
                host["data"]["custom_fields"] = d["custom_fields"]

            # Add values that do have an option for 'slug'
            host["data"]["site"] = d["site"]["slug"]
            host["data"]["role"] = d["device_role"]["slug"]
            host["data"]["model"] = d["device_type"]["slug"]

            # Attempt to add 'platform' based of value in 'slug'
            host["platform"] = d["platform"]["slug"] if d["platform"] else None

            #     "cisco_" + d["platform"]["slug"] if d["platform"] else None
            # )

            host["groups"] = ["global", d["site"]["slug"], d["device_role"]["slug"]]

            if d["site"]["slug"] not in groups.keys():
                groups[d["site"]["slug"]] = {}

            if d["device_role"]["slug"] not in groups.keys():
                groups[d["device_role"]["slug"]] = {}

            host["data"]["obj"] = NetworkImporterDevice(
                d.get("name"),
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
            hosts[d.get("name") or d.get("id")] = host

        # Pass the data back to the parent class
        super().__init__(hosts=hosts, groups=groups, defaults={}, **kwargs)


class StaticInventory(Inventory):
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

        for h in hosts:

            host: HostsDict = {"data": copy.deepcopy(base_data)}
            host["data"]["is_reacheable"] = True

            host["hostname"] = h["ip_address"]
            host["platform"] = h["platform"]
            host["groups"] = ["global"]

            host["data"]["obj"] = NetworkImporterDevice(
                h["name"], platform=host["platform"],
            )

            hosts[h["name"]] = host

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
def valid_devs(h):
    """
    

    Args:
      h: 

    Returns:

    """
    if h.data["has_config"]:
        return True
    else:
        return False


def non_valid_devs(h):
    """
    

    Args:
      h: 

    Returns:

    """
    if h.data["has_config"]:
        return False
    else:
        return True


def reacheable_devs(h):
    """
    

    Args:
      h: 

    Returns:

    """
    if h.data["is_reacheable"]:
        return True
    else:
        return False


def non_reacheable_devs(h):
    """
    

    Args:
      h: 

    Returns:

    """
    if h.data["is_reacheable"]:
        return False
    else:
        return True


def valid_and_reacheable_devs(h):
    """
    

    Args:
      h: 

    Returns:

    """
    if h.data["is_reacheable"] and h.data["has_config"]:
        return True
    else:
        return False
