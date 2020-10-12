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
# pylint: disable=invalid-name,redefined-outer-name

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Union

import toml
from pydantic import BaseSettings, ValidationError
from network_importer.adapters.netbox_api.config import AdapterSettings as NetBoxAPISettings

SETTINGS = None

DEFAULT_DRIVERS_MAPPING = {
    "default": "network_importer.drivers.default",
    "cisco_nxos": "network_importer.drivers.cisco_default",
    "cisco_ios": "network_importer.drivers.cisco_default",
    "cisco_xr": "network_importer.drivers.cisco_default",
    "juniper_junos": "network_importer.drivers.juniper_junos",
    "arista_eos": "network_importer.drivers.arista_eos",
}


class BatfishSettings(BaseSettings):

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

    address: str = "http://localhost"
    token: Optional[str]
    supported_platforms: List[str] = list()
    cacert: Optional[str]
    verify_ssl: bool = True
    request_ssl_verify: bool = False

    class Config:
        """Additional parameters to automatically map environment variable to some settings."""

        fields = {
            "address": {"env": "NETBOX_ADDRESS"},
            "token": {"env": "NETBOX_TOKEN"},
            "cacert": {"env": "NETBOX_CACERT"},
            "verify_ssl": {"env": "NETBOX_VERIFY_SSL"},
        }


class NetworkSettings(BaseSettings):

    login: Optional[str]
    password: Optional[str]
    enable: bool = True
    global_delay_factor: int = 5
    fqdns: List[str] = list()  # List of valid FQDN that can be found in the network

    class Config:
        """Additional parameters to automatically map environment variable to some settings."""

        fields = {
            "login": {"env": "NETWORK_DEVICE_LOGIN"},
            "password": {"env": "NETWORK_DEVICE_PWD"},
            "enable": {"env": "NETWORK_DEVICE_ENABLE"},
        }


class LogsSettings(BaseSettings):

    level: str = "info"  # dict(type="string", enum=["debug", "info", "warning"], default="info"),
    directory: str = "logs"
    performance_log: bool = True
    performance_log_directory: str = "performance_logs"
    # change_log: bool = True
    # change_log_format: str = "text"  # dict(type="string", enum=["jsonlines", "text"], default="text"),
    # change_log_filename: str = "changelog"


class MainSettings(BaseSettings):

    import_ips: bool = True
    import_prefixes: bool = False
    import_cabling: Union[
        bool, str
    ] = "lldp"  # =dict(type=["string", "boolean"], enum=["lldp", "cdp", "config", False], default="lldp",),
    import_transceivers: bool = False
    import_intf_status: bool = False
    import_vlans: Union[
        bool, str
    ] = "config"  # dict(type=["string", "boolean"], enum=["cli", "config", True, False], default="config",),
    generate_hostvars: bool = False
    hostvars_directory: str = "host_vars"
    nbr_workers: int = 25
    inventory_class: str = "network_importer.inventory.NetboxInventory"
    inventory_filter: str = ""
    configs_directory: str = "configs"
    data_directory: str = "data"
    data_update_cache: bool = True
    data_use_cache: bool = False
    excluded_platforms_cabling: List[str] = list()


class AdaptersSettings(BaseSettings):
    network_class: str = "network_importer.adapters.network_importer.adapter.NetworkImporterAdapter"
    sot_class: str = "network_importer.adapters.netbox_api.adapter.NetBoxAPIAdapter"
    netbox_api: NetBoxAPISettings = NetBoxAPISettings()


class DriversSettings(BaseSettings):
    mapping: Dict[str, str] = DEFAULT_DRIVERS_MAPPING


class InventorySettings(BaseSettings):
    """Parameters Specific to the inventory.

    By default, the inventory will use the primary IP to reach out to the devices
    if the use_primary_ip flag is disabled, the inventory will try to use the hostname to the device
    """

    use_primary_ip: bool = True
    fqdn: Optional[str]


class Settings(BaseSettings):
    """
    Main Settings Class for the project.
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
    """
    Load a configuration file in pyproject.toml format that contains the settings.

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
