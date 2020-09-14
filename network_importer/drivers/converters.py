import logging

from network_importer.utils import is_interface_lag
from network_importer.processors.get_neighbors import Neighbors, Neighbor
from network_importer.processors.get_vlans import Vlans, Vlan

LOGGER = logging.getLogger("network-importer")


def convert_cisco_genie_neighbors_details(device_name, data):
    """Convert the data returned by Genie for show lldp neighbors detail to Neighbors()

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
                    f"{device_name} | Neighbors, {nei_intf_name} is connected to {intf_name} but is not a valid interface (lag), SKIPPING  "
                )
                continue

            if "neighbors" not in intf_data["port_id"][nei_intf_name]:
                LOGGER.debug(f"{device_name} | No neighbor found for {nei_intf_name} connected to {intf_name}")
                continue

            if len(intf_data["port_id"][nei_intf_name]["neighbors"]) > 1:
                LOGGER.warning(
                    f"{device_name} | More than 1 neighbor found for {nei_intf_name} connected to {intf_name}, SKIPPING"
                )
                continue

            neighbor = Neighbor(
                hostname=list(intf_data["port_id"][nei_intf_name]["neighbors"].keys())[0], port=nei_intf_name
            )

            results.neighbors[intf_name].append(neighbor)

    return results


def convert_cisco_genie_vlans(device_name, data):

    results = Vlans()

    if "vlans" not in data:
        return results

    for vid, vlan_data in data["vlans"].items():
        if not vlan_data.get("name", None):
            LOGGER.warning(f"{device_name} | Unknown VLAN data, VLAN {vid}")
            continue
        elif vlan_data.get("state", None) == "unsupport":
            LOGGER.warning(f"{device_name} | Unsupported VLAN found, VLAN {vid}")
            continue
        else:
            results.vlans.append(Vlan(name=vlan_data["name"], vid=int(vlan_data["vlan_id"])))

    return results
