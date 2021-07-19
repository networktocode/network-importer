"""Settings definition for the network importer."""
# pylint: disable=invalid-name,redefined-outer-name

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Union

import toml
from pydantic import BaseSettings, ValidationError
from typing_extensions import Literal

from network_importer.exceptions import ConfigLoadFatalError

SETTINGS = None

DEFAULT_DRIVERS_MAPPING = {
    "default": "network_importer.drivers.default",
    "cisco_nxos": "network_importer.drivers.cisco_default",
    "cisco_ios": "network_importer.drivers.cisco_default",
    "cisco_xr": "network_importer.drivers.cisco_default",
    "juniper_junos": "network_importer.drivers.juniper_junos",
    "arista_eos": "network_importer.drivers.arista_eos",
}

DEFAULT_BACKENDS = {
    "netbox": {
        "inventory": "NetBoxAPIInventory",
        "adapter": "network_importer.adapters.netbox_api.adapter.NetBoxAPIAdapter",
    },
    "nautobot": {
        "inventory": "NautobotAPIInventory",
        "adapter": "network_importer.adapters.nautobot_api.adapter.NautobotAPIAdapter",
    },
}

# pylint: disable=global-statement


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
            "network_name": {"env": "BATFISH_NETWORK_NAME"},
            "snapshot_name": {"env": "BATFISH_SNAPSHOT_NAME"},
            "api_key": {"env": "BATFISH_API_KEY"},
            "port_v1": {"env": "BATFISH_PORT_V1"},
            "port_v2": {"env": "BATFISH_PORT_V2"},
            "use_ssl": {"env": "BATFISH_USE_SSL"},
        }


class NetworkSettings(BaseSettings):
    """Settings definition for the Network section of the configuration."""

    login: Optional[str]
    password: Optional[str]
    enable: bool = True

    netmiko_extras: Optional[dict]
    napalm_extras: Optional[dict]

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

    backend: Optional[Literal["nautobot", "netbox"]]
    """Only Netbox and Nautobot backend are included by default, if you want to use another backend
    you must leave backend empty and define inventory.inventory_class and adapters.sot_class manually."""

    # NOT SUPPORTED CURRENTLY
    generate_hostvars: bool = False
    hostvars_directory: str = "host_vars"


class AdaptersSettings(BaseSettings):
    """Settings definition for the Adapters section of the configuration."""

    network_class: str = "network_importer.adapters.network_importer.adapter.NetworkImporterAdapter"
    network_settings: Optional[dict]

    sot_class: Optional[str]
    sot_settings: Optional[dict]


class DriversSettings(BaseSettings):
    """Settings definition for the Drivers section of the configuration."""

    mapping: Dict[str, str] = DEFAULT_DRIVERS_MAPPING


class InventorySettings(BaseSettings):
    """Settings definition for the Inventory section of the configuration.

    By default, the inventory will use the primary IP to reach out to the devices
    if the use_primary_ip flag is disabled, the inventory will try to use the hostname to the device
    """

    inventory_class: Optional[str]
    settings: Optional[dict]

    supported_platforms: List[str] = list()


class Settings(BaseSettings):
    """Main Settings Class for the project.

    The type of each setting is defined using Python annotations
    and is validated when a config file is loaded with Pydantic.
    """

    main: MainSettings = MainSettings()
    batfish: BatfishSettings = BatfishSettings()
    logs: LogsSettings = LogsSettings()
    network: NetworkSettings = NetworkSettings()
    adapters: AdaptersSettings = AdaptersSettings()
    drivers: DriversSettings = DriversSettings()
    inventory: InventorySettings = InventorySettings()


def _configure_backend(settings: Settings):
    """Configure the inventory and the SOT adapter for a given backend.

    The inventory and/or the adapter will be updated if:
      - a backend provided is valid
      - no value has been defined already

    Args:
        settings (Settings)

    Returns:
        Settings
    """
    if not settings.main.backend and (not settings.inventory.inventory_class or not settings.adapters.sot_class):
        raise ConfigLoadFatalError(
            "You must define a valid backend or assign inventory.inventory_class and adapters.sot_class manually."
        )

    if not settings.main.backend:
        return settings

    supported_backends = DEFAULT_BACKENDS.keys()
    if settings.main.backend not in supported_backends:
        raise ConfigLoadFatalError(f"backend value one of : {', '.join(supported_backends)}")

    if not settings.inventory.inventory_class:
        settings.inventory.inventory_class = DEFAULT_BACKENDS[settings.main.backend]["inventory"]

    if not settings.adapters.sot_class:
        settings.adapters.sot_class = DEFAULT_BACKENDS[settings.main.backend]["adapter"]

    return settings


def load(config_file_name="network_importer.toml", config_data=None):
    """Load configuration.

    Configuration is loaded from a file in network_importer.toml format that contains the settings,
    or from a dictionary of those settings passed in as "config_data"

    Args:
        config_file_name (str, optional): Name of the configuration file to load. Defaults to "network_importer.toml".
        config_data (dict, optional): dict to load as the config file instead of reading the file. Defaults to None.
    """
    global SETTINGS

    if config_data:
        SETTINGS = _configure_backend(Settings(**config_data))
        return

    if os.path.exists(config_file_name):
        config_string = Path(config_file_name).read_text()
        config_tmp = toml.loads(config_string)
        SETTINGS = _configure_backend(Settings(**config_tmp))
        return

    SETTINGS = Settings()


def load_and_exit(config_file_name="network_importer.toml", config_data=None):
    """Calls load, but wraps it in a try except block.

    This is done to handle a ValidationError which is raised when settings are specified but invalid.
    In such cases, a message is printed to the screen indicating the settings which don't pass validation.

    Args:
        config_file_name (str, optional): [description]. Defaults to "network_importer.toml".
        config_data (dict, optional): [description]. Defaults to None.
    """
    try:
        load(config_file_name=config_file_name, config_data=config_data)
    except ValidationError as err:
        print(f"Configuration not valid, found {len(err.errors())} error(s)")
        for error in err.errors():
            print(f"  {'/'.join(error['loc'])} | {error['msg']} ({error['type']})")
        sys.exit(1)
    except ConfigLoadFatalError as err:
        print("Configuration not valid")
        print(f"  {err}")
        sys.exit(1)
