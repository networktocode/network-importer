import logging
from typing import List

# from nornir.core.inventory import Host
# from nornir.core.task import MultiResult, Task
from pydantic import BaseModel  # pylint: disable=no-name-in-module

# import network_importer.config as config
from network_importer.processors import BaseProcessor

LOGGER = logging.getLogger("network-importer")

# ------------------------------------------------------------
# Standard model to return for get_vlans
# ------------------------------------------------------------
class Vlan(BaseModel):
    name: str
    vid: int


class Vlans(BaseModel):
    vlans: List[Vlan] = list()


# ------------------------------------------------------------
# Processor
# ------------------------------------------------------------
class GetVlans(BaseProcessor):
    pass
