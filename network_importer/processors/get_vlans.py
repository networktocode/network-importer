"""GetVlans processor for the network_importer.

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
import logging
from typing import List

from pydantic import BaseModel  # pylint: disable=no-name-in-module

from network_importer.processors import BaseProcessor

LOGGER = logging.getLogger("network-importer")


# ------------------------------------------------------------
# Standard model to return for get_vlans
# ------------------------------------------------------------
class Vlan(BaseModel):
    """Dataclass model to store one vlan returned by get_vlans."""

    name: str
    vid: int


class Vlans(BaseModel):
    """Dataclass model to store Vlans returned by get_vlans."""

    vlans: List[Vlan] = list()


# ------------------------------------------------------------
# Processor
# ------------------------------------------------------------
class GetVlans(BaseProcessor):
    """Placeholder for GetVlans processor, currently using the BaseProcessor."""
