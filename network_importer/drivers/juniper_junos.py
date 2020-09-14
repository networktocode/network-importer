import logging

from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from network_importer.drivers.default import NetworkImporterDriver as DefaultNetworkImporterDriver
import network_importer.config as config

LOGGER = logging.getLogger("network-importer")


class NetworkImporterDriver(DefaultNetworkImporterDriver):
    """Collection of Nornir Tasks specific to Juniper Junos devices."""

    pass
