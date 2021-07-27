"""Base Inventory and Host class for Network Importer."""

from typing import Dict, List, Optional

from nornir.core.inventory import Host, Group, ConnectionOptions

# pylint: disable=too-many-arguments,too-many-instance-attributes


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
    """Base inventory class for the Network Importer."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        enable: Optional[bool] = None,
        supported_platforms: Optional[List[str]] = None,
        netmiko_extras: Optional[Dict] = None,
        napalm_extras: Optional[Dict] = None,
        limit: Optional[str] = None,
        settings: Optional[Dict] = None,
    ):
        """Initialize class and store all top level arguments locally."""
        self.username = username
        self.password = password
        self.enable = enable
        self.supported_platforms = supported_platforms
        self.limit = limit
        self.netmiko_extras = netmiko_extras
        self.napalm_extras = napalm_extras

        self.settings = settings

        # Define Global Group with Netmiko and Napalm Credentials if provided
        self.global_group = Group(
            name="global", connection_options={"netmiko": ConnectionOptions(), "napalm": ConnectionOptions()}
        )

        if self.netmiko_extras:
            self.global_group.connection_options["netmiko"].extras = self.netmiko_extras

        if self.napalm_extras:
            self.global_group.connection_options["napalm"].extras = self.napalm_extras

        # Pull the login and password from the NI config object if available
        if self.username:
            self.global_group.username = self.username

        if self.password:
            self.global_group.password = self.password
            if self.enable:
                if not self.global_group.connection_options["netmiko"].extras:
                    self.global_group.connection_options["netmiko"].extras = dict()
                elif "secret" not in self.global_group.connection_options["netmiko"].extras:
                    self.global_group.connection_options["netmiko"].extras["secret"] = self.password

                if not self.global_group.connection_options["napalm"].extras:
                    self.global_group.connection_options["napalm"].extras = {"optional_args": {"secret": self.password}}
                elif isinstance(dict, self.global_group.connection_options["napalm"].extras):
                    if "optional_args" not in self.global_group.connection_options["napalm"].extras:
                        self.global_group.connection_options["napalm"].extras["optional_args"] = {
                            "secret": self.password
                        }
                    elif isinstance(dict, self.global_group.connection_options["napalm"].extras["optional_args"]):
                        self.global_group.connection_options["napalm"].extras["optional_args"]["secret"] = self.password


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
