"""Norning Inventory for nautobot."""
# Disable too-many-arguments and too-many-locals pylint tests for this file. These are both necessary
# pylint: disable=R0913,R0914,E1101,W0613

import sys
from typing import Any, List

import pynautobot
from nornir.core.inventory import Defaults, Groups, Hosts, Inventory, ParentGroups, ConnectionOptions
from nornir.core.plugins.inventory import InventoryPluginRegister
from pydantic import ValidationError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from network_importer.adapters.nautobot_api.settings import InventorySettings
from network_importer.inventory import NetworkImporterInventory, NetworkImporterHost
from network_importer.utils import build_filter_params


class NautobotAPIInventory(NetworkImporterInventory):
    """Nautobot API Inventory Class."""

    # pylint: disable=dangerous-default-value, too-many-branches, too-many-statements
    def __init__(
        self,
        *args,
        **kwargs: Any,
    ) -> None:
        """Nornir Inventory Plugin for Nautobot API."""
        super().__init__(
            *args,
            **kwargs,
        )

        try:
            self.settings = InventorySettings(**self.settings)
        except ValidationError as exc:
            print(f"Inventory Settings are not valid, found {len(exc.errors())} error(s)")
            for error in exc.errors():
                print(f"  inventory/{'/'.join(error['loc'])} | {error['msg']} ({error['type']})")
            sys.exit(1)

        # Build Filter based on inventory_settings filter and on limit
        self.filter_parameters = {}
        if self.settings.filter is not None:
            build_filter_params(self.settings.filter.split((",")), self.filter_parameters)

        if self.limit == "False":  # Click sends limit in as a string, not a boolean.
            self.limit = False

        if self.limit:
            if "=" not in self.limit:
                self.filter_parameters["name"] = self.limit
            else:
                build_filter_params(self.limit.split((",")), self.filter_parameters)

        if "exclude" not in self.filter_parameters:
            self.filter_parameters["exclude"] = "config_context"

        # Instantiate nautobot session using pynautobot
        self.session = pynautobot.api(url=self.settings.address, token=self.settings.token)
        if not self.settings.verify_ssl:
            self.session.http_session.verify = False

        if self.settings.http_retries:
            retries = Retry(total=self.settings.http_retries,
                            backoff_factor=0.5,
                            status_forcelist=[429, 500, 502, 503, 504, ],
                            allowed_methods=False
                            )
            self.session.http_session.mount(self.session.base_url, HTTPAdapter(max_retries=retries))

    def load(self):
        """Load inventory by fetching devices from nautobot."""
        if self.filter_parameters:
            devices: List[pynautobot.modules.dcim.Devices] = self.session.dcim.devices.filter(**self.filter_parameters)
        else:
            devices: List[pynautobot.modules.dcim.Devices] = self.session.dcim.devices.all()

        # fetch all platforms from nautobot and build mapping:   platform:  napalm_driver
        platforms = self.session.dcim.platforms.all()
        platforms_mapping = {platform.slug: platform.napalm_driver for platform in platforms if platform.napalm_driver}

        hosts = Hosts()
        groups = Groups()
        defaults = Defaults()

        for dev in devices:
            # nautobot allows devices to be unnamed, but the Nornir model does not allow this
            # If a device is unnamed we will set the name to the id of the device in nautobot
            dev_name = dev.name or dev.id
            host = NetworkImporterHost(name=dev_name, connection_options=ConnectionOptions())

            # Only add virtual chassis master as inventory element
            if dev.virtual_chassis and dev.virtual_chassis.master:
                if dev.id != dev.virtual_chassis.master.id:
                    continue
                host.data["virtual_chassis"] = True

            else:
                host.data["virtual_chassis"] = False

            # If supported_platforms is provided
            # skip all devices that do not match the list of supported platforms
            # TODO need to see if we can filter when doing the query directly
            if self.supported_platforms:
                if not dev.platform:
                    continue

                if dev.platform.slug not in self.supported_platforms:
                    continue

            # Add value for IP address
            if self.settings.use_primary_ip and dev.primary_ip:
                host.hostname = dev.primary_ip.address.split("/")[0]
            elif self.settings.use_primary_ip and not dev.primary_ip:
                host.is_reachable = False
                host.not_reachable_reason = "primary ip not defined in nautobot"
            elif not self.settings.use_primary_ip and self.settings.fqdn:
                host.hostname = f"{dev.name}.{self.settings.fqdn}"
            elif not self.settings.use_primary_ip:
                host.hostname = dev.name
            else:
                host.hostname = dev_name

            host.site_name = dev.site.slug

            host.data["serial"] = dev.serial
            host.data["vendor"] = dev.device_type.manufacturer.slug
            host.data["asset_tag"] = dev.asset_tag
            host.data["custom_fields"] = dev.custom_fields
            host.data["site_id"] = dev.site.id
            host.data["device_id"] = dev.id
            host.data["role"] = dev.device_role.slug
            host.data["model"] = dev.device_type.slug

            # Attempt to add 'platform' based of value in 'slug'
            if dev.platform and dev.platform.slug in platforms_mapping:
                host.connection_options = {"napalm": ConnectionOptions(platform=platforms_mapping[dev.platform.slug])}

            if dev.platform:
                host.platform = dev.platform.slug
            else:
                host.platform = None

            host.groups = ParentGroups([self.global_group])

            if dev.site.slug not in groups.keys():
                groups[dev.site.slug] = {}

            if dev.device_role.slug not in groups.keys():
                groups[dev.device_role.slug] = {}

            if host.hostname and host.platform:
                host.is_reachable = True
            else:
                host.is_reachable = False
                host.not_reachable_reason = "hostname or platform not defined in nautobot"

            # Assign temporary dict to outer dict

            hosts[dev_name] = host

        return Inventory(hosts=hosts, groups=groups, defaults=defaults)


InventoryPluginRegister.register("NautobotAPIInventory", NautobotAPIInventory)
