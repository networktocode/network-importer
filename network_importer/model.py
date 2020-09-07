"""
(c) 2019 Network To Code

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
# pylint: disable=invalid-name,redefined-builtin
import logging
import ipaddress
from collections import defaultdict
import network_importer.config as config

from network_importer.diff import NetworkImporterDiff
from network_importer.utils import (
    expand_vlans_list,
    is_interface_physical,
    is_interface_lag,
)

from network_importer.drivers import get_driver

from network_importer.base_model import (  # pylint: disable=unused-import
    Interface,
    IPAddress,
    Optic,
    Prefix,
    Vlan,
)

from network_importer.logging import (
    changelog_create,
    changelog_delete,
    changelog_update,
)

logger = logging.getLogger("network-importer")  # pylint: disable=invalid-name


class NetworkImporterObjBase:
    """ """

    id = None
    remote = None
    local = None
    obj_type = "undefined"

    def __getattr__(self, name):
        """ """
        if self.exist_local() and hasattr(self.local, name):
            return getattr(self.local, name)

        if self.exist_remote() and hasattr(self.remote, name):
            return getattr(self.remote, name)

        raise AttributeError(f"object has no attribute '{name}'")

    def add_local(self, local):
        """ """
        self.local = local

    def update_remote(self, remote):
        """ """
        self.remote.update(remote)

    def delete_remote(self):
        """ """
        self.remote.delete()
        changelog_delete(self.obj_type, self.id, self.remote.remote.id)

    def exist_remote(self):
        """ """
        if self.remote:
            return True

        return False

    def exist_local(self):
        """ """
        if self.local:
            return True

        return False

    def diff(self):
        """ """

        if self.id:
            diff = NetworkImporterDiff(self.obj_type, self.id)
        else:
            diff = NetworkImporterDiff(self.obj_type, "undefined")

        if self.local and not self.remote:
            diff.missing_remote = True
            return diff

        if not self.local and self.remote:
            diff.missing_local = True
            return diff

        if not self.local:
            return diff

        attrs = self.local.get_attrs_diff()

        for attr in attrs:

            local = getattr(self.local, attr)
            remote = getattr(self.remote, attr)

            if isinstance(local, list):
                local = sorted(local)
            if isinstance(remote, list):
                remote = sorted(remote)

            if local != remote:
                diff.add_item(attr, local, remote)

        return diff

    def is_remote_up_to_date(self):
        """ """

        if self.diff().has_diffs():
            return False

        return True


class NetworkImporterDevice:
    """ """

    def __init__(
        self,
        name,
        hostname=None,
        platform=None,
        model=None,
        role=None,
        bf=None,
        nb=None,
        vendor=None,
        pull_cache=False,
    ):
        """


        Args:
          name:
          hostname:  (Default value = None)
          platform:  (Default value = None)
          model:  (Default value = None)
          role:  (Default value = None)
          bf:  (Default value = None)
          nb:  (Default value = None)
          vendor:  (Default value = None)
          pull_cache:  (Default value = False)

        Returns:

        """

        self.name = name
        self.hostname = hostname
        self.platform = platform
        self.model = model
        self.role = role
        self.vendor = vendor

        self.changed = False

        self.remote_id = None
        self.exist_remote = False

        self.interfaces = dict()
        self.hostvars = dict()

        # Interface to vlans mapping structure
        # {
        #    "interface_name": [ <vlan_id>, <vlan_id> ]
        # }
        self.local_interface_vlans_mapping = defaultdict(list)

        self.site = None

        self.bf = bf
        self.nr = None

        self.nb = nb
        self.remote = None

        if pull_cache:
            self.update_cache()

    def update_remote(self):
        """Update remote system, currently Netbox to match what is defined locally"""

        logger.debug(f"{self.name} | Updating remote (Netbox) ... ")

        # --------------------------------------------
        # Update or Create all Interfaces
        #  Order interfaces by type : regular, lag and lag_member last
        # --------------------------------------------

        intfs_lags = [intf for intf in self.interfaces.values() if intf.is_lag]
        intfs_lag_members = [
            intf for intf in self.interfaces.values() if intf.is_lag_member
        ]
        intfs_regs = [
            intf
            for intf in self.interfaces.values()
            if not intf.is_lag_member and not intf.is_lag
        ]

        sorted_intfs_create_update = intfs_regs + intfs_lags + intfs_lag_members

        for intf in sorted_intfs_create_update:
            self.update_interface_remote(intf)

        # --------------------------------------------
        # Delete Interfaces
        #  Order interfaces by type : regular, lag_member and lag last
        # --------------------------------------------
        sorted_intfs_delete = intfs_regs + intfs_lag_members + intfs_lags

        for intf in sorted_intfs_delete:
            if self.remote.primary_ip and intf.ip_on_interface(
                self.remote.primary_ip.address
            ):
                logger.warning(
                    f"{self.name} | Will not delete {intf.name}, currently primary mgmt interface",
                )

            if (
                not intf.exist_local()
                and intf.exist_remote()
                and not intf.ip_on_interface(self.remote.primary_ip.address)
            ):
                intf.delete_remote()

    # def diff(self):
    #     """Calculate the diff between the local object and the remote system"""
    #     diff = NetworkImporterDiff("device", self.name)

    #     for intf in self.interfaces.values():
    #         diff.add_child(intf.diff())

    #     return diff

    # def print_sync_status(self):
    #     """
    #     Check of the device is in sync between local and remote and print the status
    #     """

    #     diff = self.diff()

    #     if diff.has_diffs():
    #         logger.info(f"{self.name} | NOT up to date on the remote system")
    #     else:
    #         logger.info(f"{self.name} | up to date on the remote system")

    #     return True

    def update_interface_remote(self, intf):
        """
        Update Interface on the remote system
          Create or Update interface as needed
          Create/Update or Delete Ips as needed

        Args:
          intf:

        Returns:

        """
        if intf.exist_local():
            intf_driver = get_driver("interface")
            intf_properties = intf_driver.get_properties(intf.local)

            if config.main["import_vlans"] != "no":
                if intf.local.mode in ["TRUNK", "ACCESS"] and intf.local.access_vlan:
                    intf_properties["untagged_vlan"] = self.site.convert_vid_to_nid(
                        intf.local.access_vlan
                    )
                elif (
                    intf.local.mode in ["TRUNK", "ACCESS"]
                    and not intf.local.access_vlan
                ):
                    intf_properties["untagged_vlan"] = None

                if (
                    intf.local.mode in ["TRUNK", "L3_SUB_VLAN"]
                    and intf.local.allowed_vlans
                ):
                    intf_properties["tagged_vlans"] = self.site.convert_vids_to_nids(
                        intf.local.allowed_vlans
                    )
                elif (
                    intf.local.mode in ["TRUNK", "L3_SUB_VLAN"]
                    and not intf.local.allowed_vlans
                ):
                    intf_properties["tagged_vlans"] = []

            if intf.local.is_lag_member:
                if intf.local.parent in self.interfaces.keys():
                    if not self.interfaces[intf.local.parent].exist_remote():
                        logger.warning(
                            f"{self.name} | Interface {intf.name} is a member of lag {intf.local.parent}, but {intf.local.parent} do not exist remotely"
                        )
                    else:
                        intf_properties["lag"] = self.interfaces[
                            intf.local.parent
                        ].remote.remote.id

                else:
                    logger.warning(
                        f"{self.name} | Interface {intf.local.name} is a member of lag {intf.local.parent}, but {intf.local.parent} is not in the list"
                    )

            elif (
                not intf.local.is_lag_member
                and intf.remote
                and intf.remote.is_lag_member
            ):
                intf_properties["lag"] = None

            if intf.exist_local() and not intf.exist_remote():

                intf_properties["device"] = self.remote.id
                intf_properties["name"] = intf.name

                try:
                    remote = self.nb.dcim.interfaces.create(**intf_properties)
                except:
                    logger.warning(
                        f"{self.name} | Something went wrong while trying to create interface {intf.name} in netbox",
                        exc_info=True,
                    )
                    logger.debug(
                        f"{self.name} | {intf.name}: properties {intf_properties}"
                    )
                    return False

                intf.add_remote(remote)
                logger.debug(f"{self.name} | Interface {intf.name} created in Netbox")
                changelog_create(
                    "interface",
                    f"{self.name}::{intf.name}",
                    remote.id,
                    params=intf_properties,
                )

            elif (
                intf.exist_local()
                and intf.exist_remote()
                and intf.diff().nbr_diffs() != 0
            ):
                diff = intf.diff()
                try:
                    intf_updated = intf.remote.remote.update(data=intf_properties)
                except:
                    logger.warning(
                        f"{self.name} | Something went wrong while trying to update the interface {intf.name} in netbox",
                        exc_info=True,
                    )
                    logger.debug(
                        f"{self.name} | {intf.name}: properties {intf_properties}"
                    )
                    return False

                logger.debug(
                    f"{self.name} | Interface {intf.name} updated in Netbox: {intf_properties}"
                )
                changelog_update(
                    "interface",
                    f"{self.name}::{intf.name}",
                    intf.remote.remote.id,
                    # params=diff.items_to_dict(),
                    params=intf_properties,
                )

        # ----------------------------------------------------------
        # Update IPs
        # ----------------------------------------------------------
        for ip in intf.ips.values():
            if ip.exist_local() and not ip.exist_remote():
                try:
                    ip_address = self.nb.ipam.ip_addresses.create(
                        address=ip.address, interface=intf.remote.remote.id
                    )
                except:
                    logger.warning(
                        f"{self.name} | Something went wrong while trying to create the IP {ip.address} (intf:{intf.remote.remote.id}) in netbox",
                        exc_info=True,
                    )

                    return False

                ip.add_remote(ip_address)
                logger.debug(f"{self.name} | IP {ip.address} created in Netbox")
                changelog_create(
                    "ipaddress",
                    ip.address,
                    ip_address.id,
                    params={"interface": intf.name, "device": self.name},
                )

            # TODO need to implement IP update
            # If IP address isn't on the device, delete it from netbox, unless it's the primary IP
            elif not ip.exist_local() and ip.exist_remote():
                if (
                    self.remote.primary_ip
                    and ip.remote.address == self.remote.primary_ip.address
                ):
                    logger.warning(
                        f"{self.name} | Unable to delete IP {ip.address}, currently primary IP"
                    )
                else:
                    ip.delete_remote()
                    logger.debug(f"{self.name} | IP {ip.address} deleted in Netbox")

        # ----------------------------------------------------------
        # Update Optic is defined
        # ----------------------------------------------------------
        if intf.optic:
            if intf.optic.exist_local() and not intf.optic.exist_remote():

                optic = self.nb.dcim.inventory_items.create(
                    name=intf.optic.local.serial,
                    part_id=intf.optic.local.optic_type,
                    device=self.remote.id,
                    description=intf.name,
                    serial=intf.optic.local.serial,
                    tags=["optic"],
                )
                intf.optic.add_remote(optic)
                logger.debug(f"{self.name} | Optic for {intf.name} created in Netbox")
                changelog_create(
                    "optic",
                    intf.optic.local.serial,
                    optic.id,
                    params=dict(
                        name=intf.optic.local.serial,
                        part_id=intf.optic.local.optic_type,
                        device=self.remote.id,
                        description=intf.name,
                        serial=intf.optic.local.serial,
                        tags=["optic"],
                    ),
                )

            elif (
                intf.optic.exist_local()
                and intf.optic.exist_remote()
                and intf.optic.diff().has_diffs()
            ):

                intf.optic.remote.remote.update(
                    data=dict(
                        name=intf.optic.local.serial,
                        part_id=intf.optic.local.optic_type,
                        device=self.remote.id,
                        description=intf.name,
                        serial=intf.optic.local.serial,
                        tags=["optic"],
                    )
                )
                # TODO need to redo this part to clean it up and ensure the object gets properly updated
                logger.debug(f"{self.name} | Optic for {intf.name} updated in Netbox")
                changelog_update(
                    "optic",
                    intf.optic.local.serial,
                    intf.optic.remote.remote.id,
                    params=dict(
                        name=intf.optic.local.serial,
                        part_id=intf.optic.local.optic_type,
                        device=self.remote.id,
                        description=intf.name,
                        serial=intf.optic.local.serial,
                        tags=["optic"],
                    ),
                )

            elif not intf.optic.exist_local() and intf.optic.exist_remote():
                intf.optic.delete_remote()
                logger.debug(
                    f"{self.name} | Optic {intf.optic.remote.serial} deleted in Netbox"
                )

    def check_data_consistency(self):
        """
        Ensure the vlans configured for each interface exist in the system
        On some vendors, it's possible to have a list larger than what is really available
        """

        for intf in self.interfaces.values():
            if intf.exist_local() and intf.local.allowed_vlans:
                intf.local.allowed_vlans = [
                    vlan
                    for vlan in intf.local.allowed_vlans
                    if vlan in self.site.vlans.keys()
                ]

    def import_local_prefix(self):
        for intf_name, intf_values in self.interfaces.items():
            for ip_address, ip in self.interfaces[intf_name].ips.items():
                if not ip.local:
                    continue
                # Check the interface to vlan mapping, extract the list of vlan associated with this interface
                #  only 1 vlan supported for now
                all_local_intf_vlan_mapping = self.local_interface_vlans_mapping[
                    intf_name
                ]
                valid_local_intf_vlan_mapping = [
                    vlan
                    for vlan in all_local_intf_vlan_mapping
                    if vlan in self.site.vlans.keys()
                ]

                vlan = None
                if len(valid_local_intf_vlan_mapping) == 1:
                    vlan = valid_local_intf_vlan_mapping[0]
                elif len(self.local_interface_vlans_mapping[intf_name]) >= 1:
                    logger.warning(
                        f"{self.name} | More than 1 vlan associated with interface {intf_name} ({valid_local_intf_vlan_mapping})"
                    )

                self.site.add_prefix_from_ip(ip=ip.local.address, vlan=vlan)

    # def add_batfish_interface(self, intf_name, bf):
    #     """
    #     Add an interface to the device and try to match it with an existing interface in netbox

    #     Input: NetworkImporterInterface
    #     Output: Boolean

    #     Args:
    #       intf_name:
    #       bf:

    #     Returns:

    #     """

    #     if intf_name not in self.interfaces.keys():
    #         self.interfaces[intf_name] = NetworkImporterInterface(
    #             name=intf_name, device_name=self.name
    #         )

    #     self.interfaces[intf_name].add_batfish_interface(bf)

    #     return True

    def add_optic(self, intf_name, optic):
        """


        Args:
          intf_name:
          optic:

        Returns:

        """

        # Attached optic to interface
        # check if optic can be matched to an existing inventory items
        #  For Optic in netbox, NI is assigning the interface name to the description and a tags name "optic"
        if intf_name not in self.interfaces.keys():
            self.interfaces[intf_name] = NetworkImporterInterface(
                name=intf_name, device_name=self.name
            )

        if not self.interfaces[intf_name].optic:
            self.interfaces[intf_name].optic = NetworkImporterOptic(optic.serial)

        self.interfaces[intf_name].optic.local = optic

    def add_ip(self, intf_name, ip):
        """
        Add an IP to an existing interface and try to match the IP with an existing IP in netbox
        The match is done based on a local cache

        Inputs:
            intf_name: string, name of the interface to associated the new IP with
            ip: string, ip address of the new IP

        """

        if intf_name not in self.interfaces.keys():
            self.interfaces[intf_name] = NetworkImporterInterface(
                name=intf_name, device_name=self.name
            )

        if not ip.address in self.interfaces[intf_name].ips.keys():
            self.interfaces[intf_name].ips[ip.address] = NetworkImporterIP(
                address=ip.address
            )

        if not self.interfaces[intf_name].ips[ip.address].exist_local():
            self.interfaces[intf_name].ips[ip.address].add_local(ip)
        else:
            self.interfaces[intf_name].ips[ip.address].update_local(ip)

    def get_remote_cables(self):
        """ """

        cables = {}

        for intf in self.interfaces.values():
            if not intf.remote and not intf.remote.remote:
                continue

            if intf.remote.remote.connected_endpoint_type == "dcim.interface":

                cable_driver = get_driver("cable")
                cable = cable_driver()
                cable.add(interface=intf.remote.remote)
                # cable.add_device(self.name, self.intf.name)

                if cable.unique_id not in cables.keys():
                    cables[cable.unique_id] = cable
                else:
                    logger.debug(
                        f"{self.name} | Cable {cable.unique_id} is present more than once on this device"
                    )

        return cables

    def update_cache(self):
        """ """

        if self.nb:
            self._get_remote_interfaces_list()
            self._get_remote_ips_list()
            if config.main["import_transceivers"]:
                self._get_remote_inventory_list()

        return True

    # def _get_remote_interfaces_list(self):
    #     """Query Netbox for the remote interfaces and keep them in cache"""

    #     if not self.nb:
    #         return False

    #     intfs = self.nb.dcim.interfaces.filter(device=self.name)

    #     logger.debug(
    #         f"{self.name} - _get_remote_interfaces_list(), found {len(intfs)} interfaces"
    #     )

    #     for intf in intfs:

    #         if intf.name not in self.interfaces.keys():
    #             self.interfaces[intf.name] = NetworkImporterInterface(
    #                 name=intf.name, device_name=self.name
    #             )

    #         if not self.interfaces[intf.name].exist_remote():
    #             self.interfaces[intf.name].add_remote(intf)
    #         else:
    #             self.interfaces[intf.name].update_remote(intf)

    #     return True

    # def _get_remote_ips_list(self):
    #     """Query Netbox for all IPs associated with this device and keep them in cache"""

    #     ips = self.nb.ipam.ip_addresses.filter(device=self.name)

    #     logger.debug(f"{self.name} - _get_remote_ips_list(), found {len(ips)} ips")

    #     for ip in ips:
    #         if not ip.interface:
    #             logger.warning(
    #                 f"{self.name} - {ip.address} is not associated with an interface .. skipping"
    #             )
    #             continue

    #         intf_name = ip.interface.name
    #         if ip.interface.name not in self.interfaces.keys():
    #             self.interfaces[intf_name] = NetworkImporterInterface(
    #                 name=intf_name, device_name=self.name
    #             )

    #         if ip.address not in self.interfaces[intf_name].ips.keys():
    #             self.interfaces[intf_name].ips[ip.address] = NetworkImporterIP(
    #                 address=ip.address
    #             )

    #         if not self.interfaces[intf_name].ips[ip.address].exist_remote():
    #             self.interfaces[intf_name].ips[ip.address].add_remote(ip)
    #         else:
    #             self.interfaces[intf_name].ips[ip.address].update_remote(ip)

    #     return True

    def _get_remote_inventory_list(self):
        """
        Query Netbox for the remote inventory items to find transceiver

        """

        items = self.nb.dcim.inventory_items.filter(device=self.name)

        logger.debug(
            f"{self.name} - _get_remote_inventory_list(), found {len(items)} inventory items"
        )

        # --------------------------------------------------
        # Capture Optics
        #  Only match item with the tags 'optic'
        #  Interface name is expected to be in the description field
        # --------------------------------------------------

        for item in items:
            if "optic" not in item.tags:
                continue

            if item.description is None or item.description == "":
                continue

            intf_name = item.description
            if intf_name not in self.interfaces.keys():
                self.interfaces[intf_name] = NetworkImporterInterface(
                    name=intf_name, device_name=self.name
                )

            if not self.interfaces[intf_name].optic:
                self.interfaces[intf_name].optic = NetworkImporterOptic()

            if not self.interfaces[intf_name].optic.exist_remote():
                self.interfaces[intf_name].optic.add_remote(item)
            else:
                self.interfaces[intf_name].optic.update_remote(item)

        return True


class NetworkImporterInterface(NetworkImporterObjBase):
    """ """

    obj_type = "interface"

    def __init__(self, name, device_name):
        """

        Args:
          name:
          device_name:

        Returns:

        """
        self.id = name
        self.name = name
        self.device_name = device_name
        self.bf = None
        self.optic = None
        self.ips = dict()
        self.mtu = None

    def add_batfish_interface(self, bf):
        """
        Add a Batfish Interface Object and extract all relevant information if not already defined

        Input
            Batfish interfaceProperties object

        Args:
          bf:

        Returns:

        """

        self.bf = bf

        if not self.local:
            self.local = Interface(name=self.name)
            self.local.device_name = self.device_name

        is_physical = is_interface_physical(self.name)
        is_lag = is_interface_lag(self.name)

        if is_lag:
            self.local.is_lag = True
            self.local.is_virtual = False
        elif is_physical == False:  # pylint: disable=C0121
            self.local.is_virtual = True
        else:
            self.local.is_virtual = False

        if is_physical and self.local.speed:
            self.local.speed = int(bf.Speed)

        if self.local.mtu is None:
            self.mtu = bf.MTU

        if self.local.switchport_mode is None:
            self.local.switchport_mode = bf.Switchport_Mode

        if self.local.switchport_mode == "FEX_FABRIC":
            self.local.switchport_mode = "NONE"

        if self.local.active is None and config.main["import_intf_status"]:
            self.local.active = bf.Active
        elif not config.main["import_intf_status"]:
            self.local.active = None

        if self.local.description is None and bf.Description:
            self.local.description = bf.Description
        elif self.local.description is None:
            self.local.description = ""

        if (
            self.local.is_lag is None
            and self.local.lag_members is None
            and len(list(bf.Channel_Group_Members)) != 0
        ):
            self.local.lag_members = list(bf.Channel_Group_Members)
            self.local.is_lag = True
            self.local.is_virtual = False
        elif self.local.is_lag is None:
            self.local.is_lag = False

        if self.local.mode is None and self.local.switchport_mode:
            if bf.Encapsulation_VLAN:
                self.local.mode = "L3_SUB_VLAN"
                self.local.allowed_vlans = [bf.Encapsulation_VLAN]
            else:
                self.local.mode = self.local.switchport_mode

        if self.local.mode == "TRUNK":
            self.local.allowed_vlans = expand_vlans_list(bf.Allowed_VLANs)
            if bf.Native_VLAN:
                self.local.access_vlan = bf.Native_VLAN

        elif self.local.mode == "ACCESS" and bf.Access_VLAN:
            self.local.access_vlan = bf.Access_VLAN

        if (
            self.local.is_lag is False
            and self.local.is_lag_member is None
            and bf.Channel_Group
        ):
            self.local.parent = bf.Channel_Group
            self.local.is_lag_member = True
            self.local.is_virtual = False

    # def add_ip(self, ip):
    #     """
    #     Add new IP address to the interface

    #     Args:
    #       ip:

    #     Returns:

    #     """
    #     if ip.address in self.ips.keys():
    #         return True

    #     self.ips[ip.address] = ip

    #     logger.debug(f"Intf {self.name}, added ip {ip.address}")
    #     return True

    # def add_remote(self, remote):
    #     """

    #     Args:
    #       remote:

    #     Returns:

    #     """
    #     intf_driver = get_driver("interface")
    #     self.remote = intf_driver()
    #     self.remote.add(remote)

    #     return True

    # def diff(self):
    #     """ """

    #     diff = super().diff()

    #     for ip in self.ips.values():
    #         diff.add_child(ip.diff())

    #     if self.optic:
    #         diff.add_child(self.optic.diff())

    #     return diff

    def ip_on_interface(self, ip_addr):
        """Examine IP to determine if it exists on this interface

        Args:
            ip_addr (:obj:`NetworkImporterIP`): IP address object to be examined

        Returns:
            bool: indicates whether (True) or not (False) the IP address passed
                  into the function exists on this interface
        """

        return ip_addr in self.ips.keys()


class NetworkImporterSite:
    """ """

    def __init__(self, name, nb=None):
        """


        Args:
          name:
          nb:  (Default value = None)

        Returns:

        """

        self.name = name
        self.remote = None

        self.nb = nb

        self.vlans = dict()
        self.prefixes = dict()

        if self.nb:
            self.remote = self.nb.dcim.sites.get(slug=self.name)
            if self.remote:
                self._get_remote_vlans_list()
                self._get_remote_prefixes_list()

    def update_remote(self):  # pylint: disable=inconsistent-return-statements
        """
        Update Site and all associated resources in the Remote System
        Currently only Netbox is supported

        Args:

        Returns:

        """

        logger.info(f"Site {self.name}, Updating remote (Netbox) ... ")

        if config.main["import_vlans"] != "no":
            self.update_vlan_remote()

        if config.main["import_prefixes"]:
            self.update_prefix_remote()

    def update_vlan_remote(self):
        """
        Update Vlans on the remote system
        """
        for vlan in self.vlans.values():
            if vlan.exist_local() and not vlan.exist_remote():
                remote = self.nb.ipam.vlans.create(
                    vid=vlan.local.vid, name=vlan.local.name, site=self.remote.id
                )
                logger.debug(
                    f"Site {self.name}, created vlan {vlan.local.vid} ({remote.id}) in netbox"
                )
                vlan.add_remote(remote)
                changelog_create(
                    "vlan",
                    vlan.local.vid,
                    remote.id,
                    params=dict(name=vlan.local.name, site=self.remote.id),
                )

            elif vlan.exist_local() and vlan.exist_remote():
                vlan.update_remote_status()

            # TODO Disabling that for now, need to be sure there is no side effect when running with --limit
            # elif not vlan.exist_local() and vlan.exist_remote():
            #     vlan.delete_remote()

    def update_prefix_remote(self):
        """
        Update Prefix on the remote system
        """

        for prefix in self.prefixes.values():

            params = dict(prefix=prefix.prefix, site=self.remote.id)

            if prefix.vlan and prefix.vlan.exist_remote():
                params["vlan"] = prefix.vlan.remote.remote.id

            if prefix.exist_local() and not prefix.exist_remote():

                remote = self.nb.ipam.prefixes.create(**params)
                logger.debug(
                    f"Site {self.name}, created prefix {prefix.local.prefix} ({remote.id}) in NetBox"
                )
                prefix.add_remote(remote)
                changelog_create(
                    "prefix", prefix.local.prefix, remote.id, params=params,
                )

            elif (
                prefix.exist_local()
                and prefix.exist_remote()
                and not prefix.is_remote_up_to_date()
            ):
                prefix.remote.remote.update(data=params)
                logger.debug(
                    f"Site {self.name}, updated prefix {prefix.local.prefix} ({prefix.remote.remote.id}) in NetBox ({params})"
                )
                prefix.update_remote(prefix.remote.remote)
                changelog_update(
                    "prefix",
                    prefix.local.prefix,
                    prefix.remote.remote.id,
                    params=params,
                )

    def add_vlan(self, vlan: Vlan, device=None):
        """
        Vlan object

        Args:
          vlan:
          device: (Default value = None)

        Returns:
        """

        vid = vlan.vid

        if vid not in self.vlans.keys():
            self.vlans[vid] = NetworkImporterVlan(site=self.name, vid=vlan.vid)

        if not self.vlans[vid].exist_local():
            self.vlans[vid].add_local(vlan)
            logger.debug(f"Site {self.name} | Vlan {vid} added (local)")

        if device:
            self.vlans[vid].add_related_device(device)

        return True

    def add_prefix_from_ip(self, ip, vlan=None):
        """
        Add a prefix to the site based on an IP address
        - Identify the prefix associated with the ip address
        - Ignore network with only 1 hosts (/32)
        - Check if the NIPrefix object already exist, if not create it
        - Check if the local object already exist, if not create it

        Args:
            ip: str 1.2.3.4/24
            vlan: int Vlan ID of a Potential vlan associated with this prefix
        """
        prefix = ipaddress.ip_network(ip, strict=False)

        # If the prefix has only 1 ip it's a loopback and not a prefix
        if prefix.num_addresses == 1:
            return False

        associated_vlan = None
        if vlan and vlan in self.vlans.keys():
            associated_vlan = self.vlans[vlan]

        prefix_str = str(prefix)
        if prefix_str not in self.prefixes.keys():
            self.prefixes[prefix_str] = NetworkImporterPrefix(prefix=prefix_str)

        if associated_vlan:
            self.prefixes[prefix_str].vlan = associated_vlan

        if not self.prefixes[prefix_str].exist_local():
            self.prefixes[prefix_str].add_local(Prefix(prefix=prefix_str, vlan_id=vlan))
            logger.debug(
                f"Site {self.name} | Prefix {prefix_str} - VLAN={vlan} added (local)"
            )
        elif (
            self.prefixes[prefix_str].exist_local()
            and not self.prefixes[prefix_str].local.vlan
            and vlan
        ):
            self.prefixes[prefix_str].add_local(Prefix(prefix=prefix_str, vlan_id=vlan))
            logger.debug(
                f"Site {self.name} | Prefix {prefix_str} - VLAN={vlan} added (local)"
            )

    def convert_vids_to_nids(self, vids):
        """
        Convert Vlan IDs into Vlan Netbox IDs

        Args:
          vids: List of Vlan ID

        Returns:
            List of Netbox Vlan ID
        """

        output = []

        for vid in vids:

            nvid = self.convert_vid_to_nid(vid)

            if isinstance(nvid, int):
                output.append(nvid)

        return output

    def convert_vid_to_nid(self, vid):
        """
        Convert Vlan IDs into Vlan Netbox IDs

        Input: List of Vlan IDs
        Output: List of Netbox Vlan IDs

        Args:
          vid:

        Returns:

        """

        if vid not in self.vlans.keys():
            return None

        if not self.vlans[vid].exist_remote():
            return None

        return self.vlans[vid].remote.remote.id

    def _get_remote_vlans_list(self):
        """Query Netbox for all Vlans associated with this site and keep them in cache"""

        if config.main["import_vlans"] == "no":
            return False

        vlans = self.nb.ipam.vlans.filter(site=self.name)

        logger.debug(
            f"{self.name} - _get_remote_vlans_list(), found {len(vlans)} vlans"
        )

        for vlan in vlans:
            vid = vlan.vid
            if vid not in self.vlans.keys():
                self.vlans[vid] = NetworkImporterVlan(site=self.name, vid=vlan.vid)

            if not self.vlans[vid].exist_remote():
                self.vlans[vid].add_remote(vlan)
            else:
                self.vlans[vid].update_remote(vlan)

        return True

    def _get_remote_prefixes_list(self):
        """Query Netbox for all prefixes associated with this site and keep them in cache"""

        if not config.main["import_prefixes"]:
            return False

        prefixes = self.nb.ipam.prefixes.filter(site=self.name)

        logger.debug(
            f"{self.name} - _get_remote_prefixes_list(), found {len(prefixes)} prefixes"
        )

        for prefix in prefixes:

            if prefix.prefix not in self.prefixes.keys():
                associated_vlan = None
                if prefix.vlan and prefix.vlan.vid in self.vlans.keys():
                    associated_vlan = self.vlans[prefix.vlan.vid]

                self.prefixes[prefix.prefix] = NetworkImporterPrefix(
                    prefix=prefix.prefix, vlan=associated_vlan
                )

            if not self.prefixes[prefix.prefix].exist_remote():
                self.prefixes[prefix.prefix].add_remote(prefix)
            else:
                self.prefixes[prefix.prefix].update_remote(prefix)

        return True

    # def diff(self):
    #     """ """

    #     diff = NetworkImporterDiff("site", self.name)

    #     for vlan in self.vlans.values():
    #         diff.add_child(vlan.diff())

    #     for prefix in self.prefixes.values():
    #         diff.add_child(prefix.diff())

    #     return diff


class NetworkImporterVlan(NetworkImporterObjBase):
    """ """

    obj_type = "vlan"

    def __init__(self, site, vid):
        """


        Args:
          site:
          vid:

        Returns:

        """
        self.id = f"{site}-{vid}"

    def update_remote_status(self):
        """ """

        diff = self.diff()

        # Check if we need to add a

        missing_devices_on_remote = []

        # For each related device locally ensure it's present in the remote system
        if self.exist_local() and self.exist_remote():

            for dev_name in self.local.related_devices:
                if dev_name not in self.remote.related_devices:
                    missing_devices_on_remote.append(dev_name)

            if missing_devices_on_remote:
                diff.add_item("related_devices", missing_devices_on_remote, [])

        if diff.has_diffs():

            tags = self.remote.remote.tags
            if missing_devices_on_remote:
                tags = tags + [f"device={dev}" for dev in missing_devices_on_remote]

            self.remote.remote.update(
                data=dict(name=self.local.name, vid=self.local.vid, tags=tags)
            )
            return True

        return False

    def add_remote(self, remote):
        """


        Args:
          remote:

        Returns:

        """
        vlan_driver = get_driver("vlan")
        self.remote = vlan_driver()
        self.remote.add(remote)

    def add_related_device(self, dev_name):
        """


        Args:
          dev_name:

        Returns:

        """
        if not self.local:
            return False

        if dev_name not in self.local.related_devices:
            self.local.related_devices.append(dev_name)
            return True

        return False


class NetworkImporterPrefix(NetworkImporterObjBase):
    """ """

    obj_type = "prefix"

    def __init__(self, prefix, vlan=None):
        """

        Args:
          prefix: str

        """
        self.id = prefix
        self.prefix = prefix
        self.vlan = vlan

    def add_remote(self, remote):
        """

        Args:
          remote: object

        Returns:

        """
        prefix_driver = get_driver("prefix")
        self.remote = prefix_driver()
        self.remote.add(remote)

        return True


class NetworkImporterIP(NetworkImporterObjBase):
    """ """

    obj_type = "ipaddress"

    def __init__(self, address):
        """

        Args:
          address:

        """
        self.id = address
        self.address = address

    def add_remote(self, remote):
        """

        Args:
          remote:

        Returns:

        """
        ip_driver = get_driver("ip_address")
        self.remote = ip_driver()
        self.remote.add(remote)

        return True


class NetworkImporterOptic(NetworkImporterObjBase):
    """ """

    obj_type = "optic"

    def __init__(self, id=None):
        """

        Args:
          id:

        Returns:

        """
        self.id = id

    def add_remote(self, remote):
        """

        Args:
          remote:

        Returns:

        """
        optic_driver = get_driver("optic")
        self.remote = optic_driver()
        self.remote.add(remote)

        if not self.id and self.remote.serial:
            self.id = self.remote.serial

        return True


class NetworkImporterCable(NetworkImporterObjBase):

    obj_type = "cable"

    def __init__(self, id=None):
        """ """
        self.id = id
        self.is_valid = None
        self.interfaces = {}

    def add_interface(self, intf):
        """
        Attached a NetworkImporterInterface object to the cable
        The object will be used later to create or update the cable
        """

        side = None
        if "a" not in self.interfaces.keys():
            side = "a"
        elif "z" not in self.interfaces.keys():
            side = "z"
        else:
            raise Exception(
                f"NetworkImporterCable {self.id}, Maximum number of interfaces already reached"
            )

        self.interfaces[side] = intf

        return True

    def update_remote(self, nb):  # pylint: disable=W0221
        """ """
        if not self.is_valid:
            return False

        if self.local and self.remote:
            return False

        if not self.local and self.remote:
            logger.debug(f"Cable {self.id} not present locally, deleting in netbox .. ")
            self.remote.delete()
            return True

        if self.local and not self.remote:

            if "a" not in self.interfaces or "z" not in self.interfaces:

                logger.warning(
                    f"Unable to create cable {self.id} in Netbox, both interfaces are not present"
                )
                return False

            if (
                not self.interfaces["a"].remote.remote
                or not self.interfaces["z"].remote.remote
            ):

                logger.warning(
                    f"Unable to create cable {self.id} in Netbox, both interfaces do not have a remote object"
                )
                return False

            logger.info(f"Cable {self.id} not present will create it in netbox ")

            nbc = nb.dcim.cables.create(
                termination_a_type="dcim.interface",
                termination_a_id=self.interfaces["a"].remote.remote.id,
                termination_b_type="dcim.interface",
                termination_b_id=self.interfaces["z"].remote.remote.id,
            )

            cable_driver = get_driver("cable")
            self.remote = cable_driver()
            self.remote.add(cable=nbc)

    def get_device_intf(self, side):
        """
        Return the device name or the interface name of either side A or side Z of the cable
        """

        if self.remote:
            return self.remote.get_device_intf(side)

        if self.local:
            return self.local.get_device_intf(side)

        return None, None
