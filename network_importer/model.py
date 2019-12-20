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
import logging
import pdb
import network_importer.config as config

from network_importer.diff import NetworkImporterDiff
from network_importer.utils import expand_vlans_list
from network_importer.remote.netbox import (
    VlanRemote,
    InterfaceRemote,
    IPAddressRemote,
    OpticRemote,
    get_netbox_interface_properties,
)
from network_importer.base_model import Interface, IPAddress, Optic, Vlan

from network_importer.logging import (
    changelog_create,
    changelog_delete,
    changelog_update,
)

logger = logging.getLogger("network-importer")


class NetworkImporterObjBase(object):
    """ """

    id = None
    remote = None
    local = None
    obj_type = "undefined"

    def add_local(self, local):
        """
        

        Args:
          local: 

        Returns:

        """
        self.local = local

    def update_remote(self, remote):
        """
        

        Args:
          remote: 

        Returns:

        """
        self.remote.update_remote_info(remote)

    def delete_remote(self):
        """ """
        self.remote.delete()
        changelog_delete(self.obj_type, self.id, self.remote.remote.id)

    def exist_remote(self):
        """ """
        if self.remote:
            return True

    def exist_local(self):
        """ """
        if self.local:
            return True

    def diff(self):
        """ """

        diff = NetworkImporterDiff(self.obj_type, self.id)
        if self.local and not self.remote:
            diff.missing_remote = True
            return diff

        elif not self.local and self.remote:
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
        else:
            return True


class NetworkImporterDevice(object):
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

        self.site = None

        self.bf = bf
        self.nr = None

        self.nb = nb
        self.remote = None

        if pull_cache:
            self.update_cache()

    # def __repr__(self):
    #     return "Test()"
    # def __str__(self):
    #      return "member of Test"

    def update_remote(self):
        """Update remote system, currently Netbox to match what is defined locally"""

        logger.debug(f"Device {self.name}, Updating remote (Netbox) ... ")

        # --------------------------------------------
        # Update or Create all Interfaces
        #  Order interfaces by type : regular, lag and lag_member last
        # --------------------------------------------

        intfs_lags = [intf for intf in self.interfaces.values() if intf.is_lag()]
        intfs_lag_members = [
            intf for intf in self.interfaces.values() if intf.is_lag_member()
        ]
        intfs_regs = [
            intf
            for intf in self.interfaces.values()
            if not intf.is_lag_member() and not intf.is_lag()
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
            if not intf.exist_local() and intf.exist_remote():
                intf.delete_remote()

    def diff(self):
        """Calculate the diff between the local object and the remote system"""
        diff = NetworkImporterDiff("device", self.name)

        for intf in self.interfaces.values():
            diff.add_child(intf.diff())

        return diff

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
            intf_properties = get_netbox_interface_properties(intf.local)

            # Hack for VMX to set the interface type properly
            if self.vendor and self.vendor == "juniper" and "." not in intf.name:
                intf_properties["type"] = 1100

            if config.main["import_vlans"] != "no":
                if intf.local.mode in ["TRUNK", "ACCESS"] and intf.local.access_vlan:
                    intf_properties["untagged_vlan"] = self.site.convert_vid_to_nid(
                        intf.local.access_vlan
                    )

                if intf.local.mode == "TRUNK" and intf.local.allowed_vlans:
                    intf_properties["tagged_vlans"] = self.site.convert_vids_to_nids(
                        intf.local.allowed_vlans
                    )

            if intf.local.is_lag_member:
                if intf.local.parent in self.interfaces.keys():
                    if not self.interfaces[intf.local.parent].exist_remote():
                        logger.warning(
                            f" {self.name} | Interface {intf.name} has is a member of lag {intf.local.parent}, but {intf.local.parent} do not exist remotely"
                        )
                    else:
                        intf_properties["lag"] = self.interfaces[
                            intf.local.parent
                        ].remote.remote.id

                else:
                    logger.warning(
                        f" {self.name} | Interface {intf.local.name} has is a member of lag {intf.local.parent}, but {intf.local.parent} is not in the list"
                    )

            if intf.exist_local() and not intf.exist_remote():

                intf_properties["device"] = self.remote.id
                intf_properties["name"] = intf.name

                remote = self.nb.dcim.interfaces.create(**intf_properties)
                intf.add_remote(remote)
                logger.debug(f" {self.name} | Interface {intf.name} created in Netbox")
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
                intf_updated = intf.remote.remote.update(data=intf_properties)
                logger.debug(
                    f" {self.name} | Interface {intf.name} updated in Netbox: {intf_properties}"
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
                ip_address = self.nb.ipam.ip_addresses.create(
                    address=ip.address, interface=intf.remote.remote.id
                )
                ip.add_remote(ip_address)
                logger.debug(f" {self.name} | IP {ip.address} created in Netbox")
                changelog_create(
                    "ipaddress",
                    ip.address,
                    ip_address.id,
                    params={"interface": intf.name, "device": self.name},
                )

            # TODO need to implement IP update

            elif not ip.exist_local() and ip.exist_remote():
                ip.delete_remote()
                logger.debug(f" {self.name} | IP {ip.address} deleted in Netbox")

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
                logger.debug(f" {self.name} | Optic for {intf.name} created in Netbox")
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
                logger.debug(f" {self.name} | Optic for {intf.name} updated in Netbox")
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
                    f" {self.name} | Optic {intf.optic.remote.serial} deleted in Netbox"
                )

    def check_data_consistency(self):
        """ """

        # Ensure the vlans configured for each interface exist in the system
        #  On some devices, it's possible tp define a list larger than what is really available
        for intf in self.interfaces.values():
            if intf.exist_local() and intf.local.allowed_vlans:
                intf.local.allowed_vlans = [
                    vlan
                    for vlan in intf.local.allowed_vlans
                    if vlan in self.site.vlans.keys()
                ]

    def add_batfish_interface(self, intf_name, bf):
        """
        Add an interface to the device and try to match it with an existing interface in netbox
        
        Input: NetworkImporterInterface
        Output: Boolean

        Args:
          intf_name: 
          bf: 

        Returns:

        """

        if intf_name not in self.interfaces.keys():
            self.interfaces[intf_name] = NetworkImporterInterface(
                name=intf_name, device_name=self.name
            )

        self.interfaces[intf_name].add_batfish_interface(bf)

        return True

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
            self.interfaces[intf_name].optic = NetworkImporterOptic()

        self.interfaces[intf_name].optic.local = optic

    def add_ip(self, intf_name, ip):
        """
        Add an IP to an existing interface and try to match the IP with an existing IP in netbox
        THe match is done based on a local cache
        
        Inputs:
            intf_name: string, name of the interface to associated the new IP with
            address: string, ip address of the new IP

        Args:
          intf_name: 
          ip: 

        Returns:

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

    def update_cache(self):
        """ """

        if self.nb:
            self._get_remote_interfaces_list()
            self._get_remote_ips_list()
            self._get_remote_inventory_list()

        return True

    def _get_remote_interfaces_list(self):
        """Query Netbox for the remote interfaces and keep them in cache"""

        if not self.nb:
            return False

        intfs = self.nb.dcim.interfaces.filter(device=self.name)

        logger.debug(
            f"{self.name} - _get_remote_interfaces_list(), found {len(intfs)} interfaces"
        )

        for intf in intfs:

            if intf.name not in self.interfaces.keys():
                self.interfaces[intf.name] = NetworkImporterInterface(
                    name=intf.name, device_name=self.name
                )

            if not self.interfaces[intf.name].exist_remote():
                self.interfaces[intf.name].add_remote(intf)
            else:
                self.interfaces[intf.name].update_remote(intf)

        return True

    def _get_remote_ips_list(self):
        """Query Netbox for all IPs associated with this device and keep them in cache"""

        ips = self.nb.ipam.ip_addresses.filter(device=self.name)

        logger.debug(f"{self.name} - _get_remote_ips_list(), found {len(ips)} ips")

        for ip in ips:
            if not ip.interface:
                logger.warning(
                    f"{self.name} - {ip.address} is not associated with an interface .. skipping"
                )
                continue

            intf_name = ip.interface.name
            if ip.interface.name not in self.interfaces.keys():
                self.interfaces[intf_name] = NetworkImporterInterface(
                    name=intf_name, device_name=self.name
                )

            if ip.address not in self.interfaces[intf_name].ips.keys():
                self.interfaces[intf_name].ips[ip.address] = NetworkImporterIP(
                    address=ip.address
                )

            if not self.interfaces[intf_name].ips[ip.address].exist_remote():
                self.interfaces[intf_name].ips[ip.address].add_remote(ip)
            else:
                self.interfaces[intf_name].ips[ip.address].update_remote(ip)

        return True

    def _get_remote_inventory_list(self):
        """
        Query Netbox for the remote inventory items
          Extrac

        Args:

        Returns:

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

            if item.description == None or item.description == "":
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
        super()

    def is_lag(self):
        """ """

        if self.exist_local() and self.local.is_lag:
            return True
        elif self.exist_remote() and self.remote.is_lag:
            return True

        return False

    def is_lag_member(self):
        """ """

        if self.exist_local() and self.local.is_lag_member:
            return True
        elif self.exist_remote() and self.remote.is_lag_member:
            return True

        return False

    def add_batfish_interface(self, bf):
        """
        Add a Batfish Interface Object and extract all relevant information of not already defined
        
        Input
            Batfish interfaceProperties object

        Args:
          bf: 

        Returns:

        """

        self.bf = bf

        if not self.local:
            self.local = Interface(name=self.name)

        if "port-channel" in self.name:
            self.local.is_lag = True
            self.local.is_virtual = False

        if self.local.speed is None and bf.Speed is None and not self.local.is_lag:
            self.local.is_virtual = True
        elif self.local.speed is None and not self.local.is_lag:
            self.local.speed = int(bf.Speed)
            self.local.is_virtual = False

        if self.local.mtu is None:
            self.mtu = bf.MTU

        if self.local.switchport_mode is None:
            self.local.switchport_mode = bf.Switchport_Mode

        if self.local.switchport_mode == "FEX_FABRIC":
            self.local.switchport_mode = "NONE"

        if self.local.active is None:
            self.local.active = bf.Active

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
        elif self.local.is_lag == None:
            self.local.is_lag = False

        if self.local.mode is None and self.local.switchport_mode:
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

    def add_ip(self, ip):
        """
        Add new IP address to the interface

        Args:
          ip: 

        Returns:

        """
        if ip.address in self.ips.keys():
            return True

        self.ips[ip.address] = ip

        logger.debug(f"  Intf {self.name}, added ip {ip.address}")
        return True

    def add_remote(self, remote):
        """
        

        Args:
          remote: 

        Returns:

        """

        self.remote = InterfaceRemote()
        self.remote.add_remote_info(remote)

        return True

    def diff(self):
        """ """

        diff = super().diff()

        for ip in self.ips.values():
            diff.add_child(ip.diff())

        if self.optic:
            diff.add_child(self.optic.diff())

        return diff


class NetworkImporterSite(object):
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

        if self.nb:
            self.remote = self.nb.dcim.sites.get(slug=self.name)
            if self.remote:
                self._get_remote_vlans_list()

    def update_remote(self):
        """
        Update Site and all associated resources in the Remote System
        Currently only Netbox is supported

        Args:

        Returns:

        """

        if config.main["import_vlans"] == "no":
            return False

        logger.debug(f"Site {self.name}, Updating remote (Netbox) ... ")

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

    def add_vlan(self, vlan, device=None):
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
            logger.debug(f" Site {self.name} | Vlan {vid} added (local)")

        if device:
            self.vlans[vid].add_related_device(device)

        return True

    def convert_vids_to_nids(self, vids):
        """
        Convert Vlan IDs into Vlan Netbox IDs
        
        Input: Vlan ID
        Output: Netbox Vlan ID

        Args:
          vids: 

        Returns:

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

    def diff(self):
        """ """

        diff = NetworkImporterDiff("site", self.name)

        for vlan in self.vlans.values():
            diff.add_child(vlan.diff())

        return diff


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
        super()

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

        else:
            return False

    def add_remote(self, remote):
        """
        

        Args:
          remote: 

        Returns:

        """
        self.remote = VlanRemote()
        self.remote.add_remote_info(remote)

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


class NetworkImporterIP(NetworkImporterObjBase):
    """ """

    obj_type = "ipaddress"

    def __init__(self, address):
        """
        

        Args:
          address: 

        Returns:

        """
        self.id = address
        self.address = address

    def add_remote(self, remote):
        """
        

        Args:
          remote: 

        Returns:

        """
        self.remote = IPAddressRemote()
        self.remote.add_remote_info(remote)

        return True


class NetworkImporterOptic(NetworkImporterObjBase):
    """ """

    obj_type = "optic"

    def add_remote(self, remote):
        """
        

        Args:
          remote: 

        Returns:

        """
        self.remote = OpticRemote()
        self.remote.add_remote_info(remote)

        return True
