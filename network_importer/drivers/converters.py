"""Library of function to convert data from vendor specific format to network_importer.

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

from network_importer.utils import is_interface_lag
from network_importer.processors.get_neighbors import Neighbors, Neighbor
from network_importer.processors.get_vlans import Vlans, Vlan

LOGGER = logging.getLogger("network-importer")


def convert_cisco_genie_lldp_neighbors_details(device_name, data):
    """Convert the data returned by Genie for show lldp neighbors detail to Neighbors().

    Args:
        device_name (str): the name of the device where the data was collected
        data (Dict): the parsed data returned by Genie

    Returns:
        Neighbors: List of neighbors in a Pydantic model
    """
    results = Neighbors()

    if "interfaces" not in data:
        return results

    for intf_name, intf_data in data["interfaces"].items():
        if "port_id" not in intf_data.keys():
            continue

        # intf_name = canonical_interface_name(intf_name)
        for nei_intf_name in list(intf_data["port_id"].keys()):

            # nei_intf_name_long = canonical_interface_name(nei_intf_name)
            if is_interface_lag(nei_intf_name):
                LOGGER.debug(
                    "%s | Neighbors, %s is connected to %s but is not a valid interface (lag), SKIPPING",
                    device_name,
                    nei_intf_name,
                    intf_name,
                )
                continue

            if "neighbors" not in intf_data["port_id"][nei_intf_name]:
                LOGGER.debug("%s | No neighbor found for %s connected to %s", device_name, nei_intf_name, intf_name)
                continue

            if len(intf_data["port_id"][nei_intf_name]["neighbors"]) > 1:
                LOGGER.warning(
                    "%s | More than 1 neighbor found for %s connected to %s, SKIPPING",
                    device_name,
                    nei_intf_name,
                    intf_name,
                )
                continue

            neighbor = Neighbor(
                hostname=list(intf_data["port_id"][nei_intf_name]["neighbors"].keys())[0], port=nei_intf_name
            )

            results.neighbors[intf_name].append(neighbor)

    return results


def convert_cisco_genie_cdp_neighbors_details(device_name, data):
    """Convert the data returned by Genie for show cdp neighbors detail to Neighbors().

    Args:
        device_name (str): the name of the device where the data was collected
        data (Dict): the parsed data returned by Genie

    Returns:
        Neighbors: List of neighbors in a Pydantic model
    """
    results = Neighbors()

    if "index" not in data:
        return results

    for _, intf_data in data["index"].items():
        intf_name = intf_data.get("local_interface", None)
        nei_intf_name = intf_data.get("port_id", None)
        neighbor_name = intf_data.get("device_id", None)

        if not intf_name or not nei_intf_name or not neighbor_name:
            continue

        if is_interface_lag(nei_intf_name):
            LOGGER.debug(
                "%s | Neighbors, %s is connected to %s but is not a valid interface (lag), SKIPPING",
                device_name,
                nei_intf_name,
                intf_name,
            )
            continue

        neighbor = Neighbor(hostname=neighbor_name, port=nei_intf_name)
        results.neighbors[intf_name].append(neighbor)

        # Ensure each interface no not have more than 1 neighbor
        for intf_name, value in results.neighbors.items():
            if len(value) == 1:
                continue

            LOGGER.warning(
                "%s | More than 1 neighbor found for %s, SKIPPING", device_name, intf_name,
            )
            results.neighbors[intf_name] = []

    return results


def convert_cisco_genie_vlans(device_name: str, data: dict) -> Vlans:
    """Convert data returned by Genie from "show vlans" to the Vlans object.

    Args:
        device_name (str): name if the device
        data (dict): Structured Data returned by Genie

    Returns:
        Vlans: List of Vlan in a pydantic model
    """
    results = Vlans()

    if "vlans" not in data:
        return results

    for vid, vlan_data in data["vlans"].items():
        if not vlan_data.get("name", None):
            LOGGER.warning("%s | Unknown VLAN data, VLAN %s", device_name, vid)
            continue

        if vlan_data.get("state", None) == "unsupport":
            LOGGER.debug("%s | Unsupported VLAN found, VLAN %s", device_name, vid)
            continue

        results.vlans.append(Vlan(name=vlan_data["name"], vid=int(vlan_data["vlan_id"])))

    return results
