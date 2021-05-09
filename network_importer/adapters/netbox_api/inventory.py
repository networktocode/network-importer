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
from pydantic import BaseSettings, ValidationError
import requests
import pynetbox

from nornir.core.inventory import Defaults, Group, Groups, Host, Hosts, Inventory, ParentGroups
from nornir.core.plugins.inventory import InventoryPluginRegister
from network_importer.inventory import NetworkImporterInventory, NetworkImporterHost

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

class NetboxAPIParams(BaseSettings):
    url: Optional[str] = None
    token: Optional[str] = None
    ssl_verify: Union[bool, str] = True
    username: Optional[str] = None
    password: Optional[str] = None
    enable: Optional[bool] = True
    use_primary_ip: Optional[bool] = True
    fqdn: Optional[str] = None
    supported_platforms: Optional[List[str]] = []
    filter_parameters: Optional[Dict[str, Any]] = None
    global_delay_factor: Optional[int] = 5
    banner_timeout: Optional[int] = 15
    conn_timeout: Optional[int] = 5

class NetboxAPIInventory(NetworkImporterInventory):
    """Netbox API Inventory Class."""

    # pylint: disable=dangerous-default-value, too-many-branches, too-many-statements
    def __init__(
        self,
        params: NetboxAPIParams = NetboxAPIParams(),
        **kwargs: Any,
    ) -> None:
        """Nornir Inventory Plugin for Netbox API."""

        self.params = params
        self.filter_parameters = params.filter_parameters or {}

        if "exclude" not in self.filter_parameters.keys():
            self.filter_parameters["exclude"] = "config_context"

        # Instantiate netbox session using pynetbox
        self.session = pynetbox.api(url=params.url, token=params.token)
        if not params.ssl_verify:
            session = requests.Session()
            session.verify = False
            self.session.http_session = session

        super().__init__(**kwargs)

    def load(self):

        # fetch devices from netbox
        if self.filter_parameters:
            devices: List[pynetbox.modules.dcim.Devices] = self.session.dcim.devices.filter(**self.filter_parameters)
        else:
            devices: List[pynetbox.modules.dcim.Devices] = self.session.dcim.devices.all()

        # fetch all platforms from Netbox and build mapping:   platform:  napalm_driver
        platforms = self.session.dcim.platforms.all()
        platforms_mapping = {platform.slug: platform.napalm_driver for platform in platforms if platform.napalm_driver}

        hosts = Hosts()
        groups = Groups()
        defaults = Defaults()

        global_group_options = {"netmiko": {"extras": {}}, "napalm": {"extras": {}}}
        global_group = Group(name="global")
        
        # Pull the login and password from the NI config object if available
        if self.params.username:
            global_group.username = self.params.username

        if self.params.password:
            global_group.password = self.params.password
            if self.params.enable:
                global_group_options["netmiko"]["extras"] = {
                    "secret": self.params.password,
                    "global_delay_factor": self.params.global_delay_factor,
                    "banner_timeout": self.params.banner_timeout,
                    "conn_timeout": self.params.conn_timeout,
                }
                global_group_options["napalm"]["extras"] = {"optional_args": {"secret": self.params.password}}

        global_group.connection_options = global_group_options

        for dev in devices:

            host = NetworkImporterHost()

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
            if self.params.supported_platforms:
                if not dev.platform:
                    continue

                if dev.platform.slug not in self.params.supported_platforms:
                    continue

            # Add value for IP address
            if self.params.use_primary_ip and dev.primary_ip:
                host.hostname = dev.primary_ip.address.split("/")[0]
            elif self.params.use_primary_ip and not dev.primary_ip:
                host.is_reachable = False
                host.not_reachable_reason = "primary ip not defined in Netbox"
            elif not self.params.use_primary_ip and self.params.fqdn:
                host.hostname = f"{dev.name}.{self.params.fqdn}"
            elif not self.params.use_primary_ip:
                host.hostname = dev.name

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
                host.connection_options = {"napalm": {"platform": platforms_mapping[dev.platform.slug]}}

            if dev.platform:
                host.platform = dev.platform.slug
            else:
                host.platform = None

            host.groups = ParentGroups([global_group])

            if dev.site.slug not in groups.keys():
                groups[dev.site.slug] = {}

            if dev.device_role.slug not in groups.keys():
                groups[dev.device_role.slug] = {}

            if "hostname" in host and host["hostname"] and "platform" in host and host["platform"]:
                host.is_reachable = True

            # Assign temporary dict to outer dict
            # Netbox allows devices to be unnamed, but the Nornir model does not allow this
            # If a device is unnamed we will set the name to the id of the device in netbox
            hosts[dev.name or dev.id] = host

        return Inventory(hosts=hosts, groups=groups, defaults=defaults)


InventoryPluginRegister.register("NetboxAPIInventory", NetboxAPIInventory)

