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

logger = logging.getLogger("network-importer")


class NetworkImporterDevice(object):
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

        # Batfish Object
        self.bf = bf
        self.nr = None

        # Netbox objects
        #  Nb = Global pynetbox object
        #  Remote = Device Object fro pynetbox
        self.nb = nb
        self.remote = None

        self._cache_intfs = None
        self._cache_ips = None
        self._cache_invs = None

        if pull_cache:
            self.update_cache()

    # def __repr__(self):
    #     return "Test()"
    # def __str__(self):
    #      return "member of Test"

    def update_remote(self):
        """
        Update remote system, currently Netbox to match what is defined locally
        """

        logger.debug(f"Device {self.name}, Updating remote (Netbox) ... ")

        # Update or Create all Interfaces
        intfs_lags = [intf for intf in self.interfaces.values() if intf.is_lag]
        intfs_lag_members = [
            intf for intf in self.interfaces.values() if intf.is_lag_member
        ]
        intfs_regs = [
            intf
            for intf in self.interfaces.values()
            if not intf.is_lag_member and not intf.is_lag
        ]

        sorted_intfs = intfs_regs + intfs_lags + intfs_lag_members

        for intf in sorted_intfs:
            self.update_interface_remote(intf)

    def update_interface_remote(self, intf):
        """
        Update Interface on the remote system
        """

        intf_properties = intf.get_netbox_properties()

        if not self.exist_remote:
            return False

        # Hack for VMX to set the interface type properly
        if self.vendor and self.vendor == "juniper" and "." not in intf.name:
            intf_properties["type"] = 1100

        if config.main["import_vlans"] != "no":
            if intf.mode in ["TRUNK", "ACCESS"] and intf.access_vlan:
                intf_properties["untagged_vlan"] = self.site.convert_vid_to_nid(
                    intf.access_vlan
                )

            if intf.mode == "TRUNK" and intf.allowed_vlans:
                intf_properties["tagged_vlans"] = self.site.convert_vids_to_nids(
                    intf.allowed_vlans
                )

        if intf.is_lag_member:
            if intf.parent in self.interfaces.keys():
                if not self.interfaces[intf.parent].exist_remote:
                    logger.warning(
                        f" {self.name} | Interface {intf.name} has is a member of lag {intf.parent}, but {intf.parent} do not exist remotely"
                    )
                else:
                    intf_properties["lag"] = self.interfaces[intf.parent].remote.id

            else:
                logger.warning(
                    f" {self.name} | Interface {intf.name} has is a member of lag {intf.parent}, but {intf.parent} is not in the list"
                )

        if not intf.exist_remote:
            intf_properties["device"] = self.remote.id
            intf_properties["name"] = intf.name

            ## TODO add check to ensure the interface got properly created
            intf.remote = self.nb.dcim.interfaces.create(**intf_properties)
            intf.exist_remote = True
            intf.remote_id = intf.remote.id
            logger.debug(f" {self.name} | Interface {intf.name} created in Netbox")

        elif not NetworkImporterInterface.is_remote_up_to_date(
            intf_properties, intf.remote
        ):
            intf_updated = intf.remote.update(data=intf_properties)
            logger.debug(f" {self.name} | Interface {intf.name} updated in Netbox")

        # ----------------------------------------------------------
        # Update IPs
        # ----------------------------------------------------------
        for ip in intf.ips.values():
            if not ip.exist_remote:
                ip.remote = self.nb.ipam.ip_addresses.create(
                    address=ip.address, interface=intf.remote.id
                )
                ip.exist_remote = True
                logger.debug(f" {self.name} | IP {ip.address} created in Netbox")

        # ----------------------------------------------------------
        # Update Optic is defined
        # ----------------------------------------------------------
        if intf.optic:
            if not intf.optic.exist_remote:
                intf.optic.remote = self.nb.dcim.inventory_items.create(
                    name=intf.optic.serial,
                    part_id=intf.optic.type,
                    device=self.remote.id,
                    description=intf.name,
                    serial=intf.optic.serial,
                    tags=["optic"],
                )
                intf.optic.exist_remote = True
                logger.debug(f" {self.name} | Optic for {intf.name} created in Netbox")

            elif not intf.optic.is_remote_up_to_date():
                intf.optic.remote.update(
                    data=dict(
                        name=intf.optic.serial,
                        part_id=intf.optic.type,
                        device=self.remote.id,
                        description=intf.name,
                        serial=intf.optic.serial,
                        tags=["optic"],
                    )
                )
                logger.debug(f" {self.name} | Optic for {intf.name} updated in Netbox")

    def add_interface(self, intf):
        """
        Add an interface to the device and try to match it with an existing interface in netbox

        Input: NetworkImporterInterface
        Output: Boolean
        """

        if self._cache_intfs == None and self.exist_remote:
            self._get_remote_interfaces_list()

        if self._cache_ips == None and self.exist_remote:
            self._get_remote_ips_list()

        # TODO Check if this interface already exist for this device

        if self._cache_intfs:
            if intf.name in self._cache_intfs.keys():
                intf.remote = self._cache_intfs[intf.name]
                intf.exist_remote = True

        self.interfaces[intf.name] = intf

        return True

    def add_optic(self, intf_name, optic):

        # Attached optic to interface
        # check if optic can be matched to an existing inventory items
        #  For Optic in netbox, NI is assigning the interface name to the description and a tags name "optic"
        if intf_name not in self.interfaces.keys():
            logger.warning(
                f" {self.name} | Unable to attach an optic to {intf_name}, this interface do not exist"
            )
            return False

        for item in self._cache_invs.values():
            if "optic" not in item.tags:
                continue

            if item.description == intf_name:
                optic.remote = item
                optic.exist_remote = True

        self.interfaces[intf_name].optic = optic

    def add_ip(self, intf_name, address):
        """
        Add an IP to an existing interface and try to match the IP with an existing IP in netbox
        THe match is done based on a local cache

        Inputs:
            intf_name: string, name of the interface to associated the new IP with
            address: string, ip address of the new IP
        """

        if intf_name not in self.interfaces:
            raise KeyError(f"Interface {intf_name} not present")

        ip = NetworkImporterIP(address)

        if address in self._cache_ips.keys():
            ip.remote = self._cache_ips[address]
            ip.exist_remote = True

        return self.interfaces[intf_name].add_ip(ip)


    def update_cache(self):
        
        if self.nb:
            self._get_remote_interfaces_list()
            self._get_remote_ips_list()
            self._get_remote_inventory_list()

        return True

    def _get_remote_interfaces_list(self):
        """
        Query Netbox for the remote interfaces and keep them in cache
        """

        intfs = self.nb.dcim.interfaces.filter(device=self.name)

        logger.debug(
            f"{self.name} - _get_remote_interfaces_list(), found {len(intfs)} interfaces"
        )

        if self._cache_intfs == None:
            self._cache_intfs = dict()

        if len(intfs) == 0:
            return True

        for intf in intfs:
            if intf.name in self._cache_intfs.keys():
                logger.warn(
                    f"{self.name} - Interface {intf.name} already present in cache"
                )
            self._cache_intfs[intf.name] = intf

        return True

    def _get_remote_ips_list(self):
        """
        Query Netbox for all IPs associated with this device and keep them in cache
        """

        ips = self.nb.ipam.ip_addresses.filter(device=self.name)

        logger.debug(f"{self.name} - _get_remote_ips_list(), found {len(ips)} ips")

        if self._cache_ips == None:
            self._cache_ips = dict()

        if len(ips) == 0:
            return True

        for ip in ips:
            if ip.address in self._cache_ips.keys():
                logger.warn(f"{self.name} - IPs {ip.address} already present in cache")
            self._cache_ips[ip.address] = ip

        return True

    def _get_remote_inventory_list(self):
        """
        Query Netbox for the remote inventory item and keep them in cache
        """

        items = self.nb.dcim.inventory_items.filter(device=self.name)

        logger.debug(
            f"{self.name} - _get_remote_inventory_list(), found {len(items)} inventory items"
        )

        if self._cache_invs == None:
            self._cache_invs = dict()

        if len(items) == 0:
            return True

        for item in items:
            if item.id in self._cache_invs.keys():
                logger.warn(
                    f"{self.name} - Iventory items {item.id} already present in cache"
                )
            self._cache_invs[item.id] = item

        return True


class NetworkImporterInterface(object):
    def __init__(self, name, device_name):

        self.name = name
        self.device_name = device_name

        self.mode = None  # TRUNK, ACCESS, L3
        self.remote_id = None

        self.is_virtual = None

        self.active = None
        self.is_lag_member = None
        self.parent = None
        self.is_lag = None
        self.lag_members = None

        self.description = None
        self.speed = None
        self.mtu = None
        self.switchport_mode = None

        self.access_vlan = None
        self.allowed_vlans = None
        self.ips = dict()

        self.exist_remote = False
        self.bf = None
        self.remote = None

        self.optic = None

    def add_bf_intf(self, bf):
        """
        Add a Batfish Interface Object and extract all relevant information of not already defined

        Input
            Batfish interfaceProperties object
        """

        self.bf = bf

        if self.speed is None and bf.Speed is None:
            self.is_virtual = True
        elif self.speed is None:
            self.speed = bf.Speed

        if self.mtu is None:
            self.mtu = bf.MTU

        if self.switchport_mode is None:
            self.switchport_mode = bf.Switchport_Mode

        if self.active is None:
            self.active = bf.Active

        if self.description is None:
            self.description = bf.Description

        if (
            self.is_lag is None
            and self.lag_members is None
            and len(list(bf.Channel_Group_Members)) != 0
        ):
            self.lag_members = list(bf.Channel_Group_Members)
            self.is_lag = True
        else:
            self.is_lag = False

        if self.mode is None and self.switchport_mode:
            self.mode = self.switchport_mode

        if self.mode == "TRUNK":
            self.allowed_vlans = self.expand_vlans_list(bf.Allowed_VLANs)
            if bf.Native_VLAN:
                self.access_vlan = bf.Native_VLAN

        elif self.mode == "ACCESS" and bf.Access_VLAN:
            self.access_vlan = bf.Access_VLAN

        if self.is_lag is False and self.is_lag_member is None and bf.Channel_Group:
            self.parent = bf.Channel_Group
            self.is_lag_member = True

    @staticmethod
    def expand_vlans_list(vlans):
        """
        Input:
            String (TODO add support for list)

        Return List
        """
        raw_vlans_list = []
        clean_vlans_list = []

        vlans_csv = str(vlans).split(",")

        for vlan in vlans_csv:
            min_max = str(vlan).split("-")
            if len(min_max) == 1:
                raw_vlans_list.append(vlan)
            elif len(min_max) == 2:
                raw_vlans_list.extend(range(int(min_max[0]), int(min_max[1]) + 1))

            # Pass if min_max biggest than 2

        for v in raw_vlans_list:
            try:
                clean_vlans_list.append(int(v))
            except ValueError as e:
                logger.debug(
                    f"expand_vlans_list() Unable to convert {v} as integer .. skipping"
                )

        return sorted(clean_vlans_list)

    def add_ip(self, ip):
        """
        Add new IP address to the interface
        """
        if ip.address in self.ips.keys():
            return True

        self.ips[ip.address] = ip

        logger.debug(f"  Intf {self.name}, added ip {ip.address}")
        return True

    def get_netbox_properties(self):
        """
        Get a dict with all interface properties in Netbox format 

        Input: None
        Output: Dictionnary of properties reasy to pass to netbox
        minus the vlans IDs that needs to be converted
        """

        intf_properties = dict()

        if self.is_lag:
            intf_properties["type"] = 200
        elif self.is_virtual:
            intf_properties["type"] = 0
        elif self.speed == 1000000000:
            intf_properties["type"] = 800
        elif self.speed == 1000000000:
            intf_properties["type"] = 1100
        elif self.speed == 10000000000:
            intf_properties["type"] = 1200
        elif self.speed == 25000000000:
            intf_properties["type"] = 1350
        elif self.speed == 40000000000:
            intf_properties["type"] = 1400
        elif self.speed == 100000000000:
            intf_properties["type"] = 1600
        else:
            intf_properties["type"] = 1100

        if self.mtu:
            intf_properties["mtu"] = self.mtu

        if self.description:
            intf_properties["description"] = self.description

        # TODO Add a check here to see what is the current status
        if self.switchport_mode == "ACCESS":
            intf_properties["mode"] = 100

        elif self.switchport_mode == "TRUNK":
            intf_properties["mode"] = 200

        if not self.active is None:
            intf_properties["enabled"] = self.active

        return intf_properties

    @staticmethod
    def is_remote_up_to_date(local, remote):
        """
        Static method to check if the remote (netbox) needs to be updated.
        This method is static because it's using some information that are defined at the device level right now
        Need to work on refactoring that to clean it up

        local = dict of properties ready
        remote = Pynetbox object 

        return boolean
        """

        diffs = NetworkImporterInterface.get_diff_remote(local, remote)

        if not diffs["before"] and not diffs["after"]:
            return True

        return False

    @staticmethod
    def get_diff_remote(local, remote):
        """
        Static method to get the diff of the difference between remote and local

        This method is static because it's using some information that are defined at the device level right now
        Need to work on refactoring that to clean it up

        local = dict of properties ready
        remote = Pynetbox object 
        
        return dict
        """
        diffs = {"before": {}, "after": {}}

        properties = [
            "mtu",
            "description", 
            "enabled",
            "tagged_vlan",
        ]

        for prop in properties:
            if prop in local and local[prop] != getattr(remote, prop):
                diffs["before"][prop] = getattr(remote, prop)
                diffs["after"][prop] = local[prop]

        if "mode" in local and local["mode"] != remote.mode.value:
            diffs["before"]["mode"] = remote.mode.value
            diffs["after"]["mode"] = local["mode"]

        if "type" in local and local["type"] != remote.type.value:
            diffs["before"]["type"] = remote.type.value
            diffs["after"]["type"] = local["type"]

        if "untagged_vlan" in local and local["untagged_vlan"] != remote.untagged_vlan.id:
            diffs["before"]["untagged_vlan"] = remote.untagged_vlan.id
            diffs["after"]["untagged_vlan"] = local["untagged_vlan"]

        return diffs


# TODO need to find a way to build a table to convert back and forth
# # Interface types
# # Virtual
# IFACE_TYPE_VIRTUAL = 0
# IFACE_TYPE_LAG = 200
# # Ethernet
# IFACE_TYPE_100ME_FIXED = 800
# IFACE_TYPE_1GE_FIXED = 1000
# IFACE_TYPE_1GE_GBIC = 1050
# IFACE_TYPE_1GE_SFP = 1100
# IFACE_TYPE_2GE_FIXED = 1120
# IFACE_TYPE_5GE_FIXED = 1130
# IFACE_TYPE_10GE_FIXED = 1150
# IFACE_TYPE_10GE_CX4 = 1170
# IFACE_TYPE_10GE_SFP_PLUS = 1200
# IFACE_TYPE_10GE_XFP = 1300
# IFACE_TYPE_10GE_XENPAK = 1310
# IFACE_TYPE_10GE_X2 = 1320
# IFACE_TYPE_25GE_SFP28 = 1350
# IFACE_TYPE_40GE_QSFP_PLUS = 1400
# IFACE_TYPE_50GE_QSFP28 = 1420
# IFACE_TYPE_100GE_CFP = 1500
# IFACE_TYPE_100GE_CFP2 = 1510
# IFACE_TYPE_100GE_CFP4 = 1520
# IFACE_TYPE_100GE_CPAK = 1550
# IFACE_TYPE_100GE_QSFP28 = 1600
# IFACE_TYPE_200GE_CFP2 = 1650
# IFACE_TYPE_200GE_QSFP56 = 1700
# IFACE_TYPE_400GE_QSFP_DD = 1750


class NetworkImporterSite(object):
    def __init__(self, name, nb=None):

        self.name = name
        self.remote_id = None
        self.remote = None
        self.exist_remote = False

        self.nb = nb

        self._cache_vlans = None

        self.vlans = dict()

        if self.nb:
            self.remote = self.nb.dcim.sites.get(slug=self.name)
            if self.remote:
                self.exist_remote = True
                self._get_remote_vlans_list()

    def update_remote(self):
        """
        Update Site and all associated resources in the Remote System
        Currently only Netbox is supported
        """

        if config.main["import_vlans"] != "no":
            logger.debug(f"Site {self.name}, Updating remote (Netbox) ... ")
            self.create_vlans_remote()

    def add_vlan(self, vlan):
        """
        Add Vlan to site, for each new vlan we'll try to match it with an existing vlan in Netbox
        To do the match we are using a local cache

        Input: NetworkImporterVlan Object
        Output: Boolean
        """

        if self._cache_vlans == None and self.exist_remote:
            self._get_remote_vlans_list()

        if self._cache_vlans:
            if vlan.vid in self._cache_vlans.keys():
                vlan.remote = self._cache_vlans[vlan.vid]
                vlan.exist_remote = True

        self.vlans[vlan.vid] = vlan

        logger.debug(f"Site {self.name} - add_vlan({vlan.vid}) ")

        return True

    def convert_vids_to_nids(self, vids):
        """
        Convert Vlan IDs into Vlan Netbox IDs

        Input: Vlan ID
        Output: Netbox Vlan ID
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
        """

        if vid not in self.vlans.keys():
            return None

        if not self.vlans[vid].exist_remote:
            return None

        return self.vlans[vid].remote.id

    def create_vlans_remote(self):
        """
        Create all Vlan in Netbox if they do not exist already
        """

        if config.main["import_vlans"] == "no":
            return False

        for vlan in self.vlans.values():
            if not vlan.exist_remote:
                # TODO add check to ensure the vlan is properly created
                vlan.remote = self.nb.ipam.vlans.create(
                    vid=vlan.vid, name=vlan.name, site=self.remote.id
                )
                vlan.exist_remote = True

    def _get_remote_vlans_list(self):
        """
        Query Netbox for all Vlans associated with this site and keep them in cache
        """

        if config.main["import_vlans"] == "no":
            return False

        vlans = self.nb.ipam.vlans.filter(site=self.name)

        logger.debug(
            f"{self.name} - _get_remote_vlans_list(), found {len(vlans)} vlans"
        )

        if self._cache_vlans == None:
            self._cache_vlans = dict()

        if len(vlans) == 0:
            return True

        for vlan in vlans:
            if vlan.vid in self._cache_vlans.keys():
                logger.warn(f"{self.name} - Vlan {vlan.vid} already present in cache")

            self._cache_vlans[vlan.vid] = vlan

        return True


class NetworkImporterVlan(object):
    def __init__(self, name, vid):

        self.name = name
        self.vid = int(vid)
        self.remote_id = None
        self.remote = None
        self.exist_remote = False


class NetworkImporterIP(object):
    def __init__(self, address, family=None, remote=None):

        self.address = address
        self.exist_remote = False
        self.family = None
        self.remote = None
        self.exist_remote = False


class NetworkImporterOptic(object):
    def __init__(self, optic_type, intf, serial, name):
        self.type = optic_type
        self.intf = intf
        self.serial = serial
        self.name = name

        self.remote = None
        self.exist_remote = False

    def is_remote_up_to_date(self):

        if not self.exist_remote:
            return False

        if self.name != self.remote.name:
            return False
        elif self.intf != self.remote.description:
            return False
        elif self.serial != self.remote.serial:
            return False
        elif "optic" not in self.remote.tags:
            return False

        return True
