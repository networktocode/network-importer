"""Settings definition for the network importer.

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
# pylint: disable=invalid-name,redefined-outer-name

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Union

import toml
from pydantic import BaseSettings, ValidationError
from typing_extensions import Literal

SETTINGS = None

DEFAULT_DRIVERS_MAPPING = {
    "default": "network_importer.drivers.default",
    "cisco_nxos": "network_importer.drivers.cisco_default",
    "cisco_ios": "network_importer.drivers.cisco_default",
    "cisco_xr": "network_importer.drivers.cisco_default",
    "juniper_junos": "network_importer.drivers.juniper_junos",
    "arista_eos": "network_importer.drivers.arista_eos",
}

# pylint: disable=too-few-public-methods,global-statement


class BatfishSettings(BaseSettings):
    """Settings definition for the Batfish section of the configuration."""

    address: str = "localhost"
    network_name: str = "network-importer"
    snapshot_name: str = "latest"
    port_v1: int = 9997
    port_v2: int = 9996
    use_ssl: bool = False
    api_key: Optional[str]

    class Config:
        """Additional parameters to automatically map environment variable to some settings."""

        fields = {
            "address": {"env": "BATFISH_ADDRESS"},
            "api_key": {"env": "BATFISH_API_KEY"},
        }


class NetboxSettings(BaseSettings):
    """Settings definition for the Netbox section of the configuration."""

    address: str = "http://localhost"
    token: Optional[str]
    verify_ssl: bool = True

    """Define a list of supported platform,
    if defined all devices without platform or with a different platforms will be removed from the inventory"""
    supported_platforms: List[str] = list()

    # Currently not used in 2.x, need to add them back
    # cacert: Optional[str]
    # request_ssl_verify: bool = False

    class Config:
        """Additional parameters to automatically map environment variable to some settings."""

        fields = {
            "address": {"env": "NETBOX_ADDRESS"},
            "token": {"env": "NETBOX_TOKEN"},
            "verify_ssl": {"env": "NETBOX_VERIFY_SSL"},
        }


class NetworkSettings(BaseSettings):
    """Settings definition for the Network section of the configuration."""

    login: Optional[str]
    password: Optional[str]
    enable: bool = True
    global_delay_factor: int = 5
    banner_timeout: int = 15
    conn_timeout: int = 5
    fqdns: List[str] = list()  # List of valid FQDN that can be found in the network

    class Config:
        """Additional parameters to automatically map environment variable to some settings."""

        fields = {
            "login": {"env": "NETWORK_DEVICE_LOGIN"},
            "password": {"env": "NETWORK_DEVICE_PWD"},
            "enable": {"env": "NETWORK_DEVICE_ENABLE"},
        }


class LogsSettings(BaseSettings):
    """Settings definition for the Log section of the configuration."""

    level: Literal["debug", "info", "warning"] = "info"
    # directory: str = "logs"
    performance_log: bool = False
    performance_log_directory: str = "performance_logs"
    # change_log: bool = True
    # change_log_format: Literal[
    #     "jsonlines", "text"
    # ] = "text"  # dict(type="string", enum=["jsonlines", "text"], default="text"),
    # change_log_filename: str = "changelog"


class MainSettings(BaseSettings):
    """Settings definition for the Main section of the configuration."""

    import_ips: bool = True
    import_prefixes: bool = False
    import_cabling: Union[bool, Literal["lldp", "cdp", "config", "no"]] = "lldp"
    excluded_platforms_cabling: List[str] = list()

    import_vlans: Union[bool, Literal["config", "cli", "no"]] = "config"
    import_intf_status: bool = False

    nbr_workers: int = 25

    configs_directory: str = "configs"

    # NOT SUPPORTED CURRENTLY
    generate_hostvars: bool = False
    hostvars_directory: str = "host_vars"


class AdaptersSettings(BaseSettings):
    """Settings definition for the Adapters section of the configuration."""

    network_class: str = "network_importer.adapters.network_importer.adapter.NetworkImporterAdapter"
    sot_class: str = "network_importer.adapters.netbox_api.adapter.NetBoxAPIAdapter"
    sot_params: Optional[dict]
    network_params: Optional[dict]


class DriversSettings(BaseSettings):
    """Settings definition for the Drivers section of the configuration."""

    mapping: Dict[str, str] = DEFAULT_DRIVERS_MAPPING


class InventorySettings(BaseSettings):
    """Settings definition for the Inventory section of the configuration.

    By default, the inventory will use the primary IP to reach out to the devices
    if the use_primary_ip flag is disabled, the inventory will try to use the hostname to the device
    """

    use_primary_ip: bool = True
    fqdn: Optional[str]

    inventory_class: str = "network_importer.inventory.NetboxInventory"
    filter: str = ""

    class Config:
        """Additional parameters to automatically map environment variable to some settings."""

        fields = {"inventory_filter": {"env": "INVENTORY_FILTER"}}


class Settings(BaseSettings):
    """Main Settings Class for the project.

    The type of each setting is defined using Python annotations
    and is validated when a config file is loaded with Pydantic.
    """

    main: MainSettings = MainSettings()
    netbox: NetboxSettings = NetboxSettings()
    batfish: BatfishSettings = BatfishSettings()
    logs: LogsSettings = LogsSettings()
    network: NetworkSettings = NetworkSettings()
    adapters: AdaptersSettings = AdaptersSettings()
    drivers: DriversSettings = DriversSettings()
    inventory: InventorySettings = InventorySettings()


def load(config_file_name="network_importer.toml", config_data=None):
    """Load a configuration file in pyproject.toml format that contains the settings.

    The settings for this app are expected to be in [tool.json_schema_testing] in TOML
    if nothing is found in the config file or if the config file do not exist, the default values will be used.

    Args:
        config_file_name (str, optional): Name of the configuration file to load. Defaults to "pyproject.toml".
        config_data (dict, optional): dict to load as the config file instead of reading the file. Defaults to None.
    """
    global SETTINGS

    if config_data:
        SETTINGS = Settings(**config_data)
        return

    if os.path.exists(config_file_name):
        config_string = Path(config_file_name).read_text()
        config_tmp = toml.loads(config_string)

        try:
            SETTINGS = Settings(**config_tmp)
            return
        except ValidationError as e:
            print(f"Configuration not valid, found {len(e.errors())} error(s)")
            for error in e.errors():
                print(f"  {'/'.join(error['loc'])} | {error['msg']} ({error['type']})")
            sys.exit(1)

    SETTINGS = Settings()
