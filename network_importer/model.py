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
    ):

        self.name = name
        self.hostname = hostname
        self.platform = platform
        self.model = model
        self.role = role

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

        if self.nb:
            self._get_remote_interfaces_list()
            self._get_remote_ips_list()

    def update_remote(self):
        """
        Update remote system, currently Netbox to match what is defined locally
        """
            
        logger.debug(f"Device {self.name}, Updating remote (Netbox) ... ")

        # Update or Create all Interfaces
        for intf in self.interfaces.values():

            intf_properties = intf.get_netbox_properties()
                
            if "untagged_vlan" in intf_properties and intf_properties["untagged_vlan"]:
                intf_properties["untagged_vlan"] = self.site.convert_vid_to_nid(intf_properties["untagged_vlan"])
            
            if "tagged_vlans" in intf_properties:
                intf_properties["tagged_vlans"] = self.site.convert_vids_to_nids(intf_properties["tagged_vlans"])
            
            if not intf.exist_remote:
                intf_properties["device"] = self.remote.id
                intf_properties["name"] = intf.name

                intf.remote = self.nb.dcim.interfaces.create(**intf_properties)
                logger.debug(f"{self.name} - Interface {intf.name} created in Netbox")
                
            # else:
            #     intf.remote = intf.remote.update(**intf_properties)
            #     logger.debug(f"{self.name} - Interface {intf.name} updated in Netbox")
               
            for ip in intf.ips.values():
                if not ip.exist_remote:
                    ip.remote = self.nb.ipam.ip_addresses.create(address=ip.address, interface=intf.remote.id)
                    logger.debug(f"{self.name} - IP {ip.address} created in Netbox")


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


class NetworkImporterInterface(object):
    def __init__(self, name, device_name, speed=None, mtu=None, switchport_mode=None):

        self.name = name
        self.device_name = device_name

        self.type = None
        self.remote_id = None

        self.speed = speed
        self.mtu = mtu
        self.switchport_mode = switchport_mode

        self.ips = dict()

        self.exist_remote = False
        self.bf = None
        self.remote = None

      
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

        intf_properties = {}

        if self.speed == None:
            intf_properties["type"] = 0
        elif self.speed == 1000000000:
            intf_properties["type"] = 1100

        intf_properties["mtu"] = self.mtu

         # TODO Add a check here to see what is the current status
        if self.switchport_mode == "ACCESS":
            intf_properties["mode"] = 100
            intf_properties["untagged_vlan"] = self.bf.Access_VLAN
        elif self.switchport_mode == "TRUNK":
            intf_properties["mode"] == 200
            intf_properties["tagged_vlans"] = self.bf.Allowed_VLANs

        return intf_properties

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
# # Wireless
# IFACE_TYPE_80211A = 2600
# IFACE_TYPE_80211G = 2610
# IFACE_TYPE_80211N = 2620
# IFACE_TYPE_80211AC = 2630
# IFACE_TYPE_80211AD = 2640
# # Cellular
# IFACE_TYPE_GSM = 2810
# IFACE_TYPE_CDMA = 2820
# IFACE_TYPE_LTE = 2830
# # SONET
# IFACE_TYPE_SONET_OC3 = 6100
# IFACE_TYPE_SONET_OC12 = 6200
# IFACE_TYPE_SONET_OC48 = 6300
# IFACE_TYPE_SONET_OC192 = 6400
# IFACE_TYPE_SONET_OC768 = 6500
# IFACE_TYPE_SONET_OC1920 = 6600
# IFACE_TYPE_SONET_OC3840 = 6700
# # Fibrechannel
# IFACE_TYPE_1GFC_SFP = 3010
# IFACE_TYPE_2GFC_SFP = 3020
# IFACE_TYPE_4GFC_SFP = 3040
# IFACE_TYPE_8GFC_SFP_PLUS = 3080
# IFACE_TYPE_16GFC_SFP_PLUS = 3160
# IFACE_TYPE_32GFC_SFP28 = 3320
# IFACE_TYPE_128GFC_QSFP28 = 3400
# # Serial
# IFACE_TYPE_T1 = 4000
# IFACE_TYPE_E1 = 4010
# IFACE_TYPE_T3 = 4040
# IFACE_TYPE_E3 = 4050
# # Stacking
# IFACE_TYPE_STACKWISE = 5000
# IFACE_TYPE_STACKWISE_PLUS = 5050
# IFACE_TYPE_FLEXSTACK = 5100
# IFACE_TYPE_FLEXSTACK_PLUS = 5150
# IFACE_TYPE_JUNIPER_VCP = 5200
# IFACE_TYPE_SUMMITSTACK = 5300
# IFACE_TYPE_SUMMITSTACK128 = 5310
# IFACE_TYPE_SUMMITSTACK256 = 5320
# IFACE_TYPE_SUMMITSTACK512 = 5330


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
        Update Site and all associated resources in the Remote system
        Currently only Netbox is supported
        """
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

        return [self.convert_vid_to_nid(vid) for vid in vids]


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
        for vlan in self.vlans.values():
            if not vlan.exist_remote:
                # TODO add check to ensure the vlan is properly created
                vlan.remote = self.nb.ipam.vlans.create(
                    vid=vlan.vid, name=f"vlan-{vlan.vid}", site=self.name
                )
                vlan.exist_remote = True



    def _get_remote_vlans_list(self):
        """
        Query Netbox for all Vlans associated with this site and keep them in cache
        """

        vlans = self.nb.ipam.vlans.filter(site=self.name)

        logger.debug(
            f"{self.name} - _get_remote_vlans_list(), found {len(vlans)} vlans"
        )

        if len(vlans) == 0:
            return True

        if self._cache_vlans == None:
            self._cache_vlans = dict()

        for vlan in vlans:
            if vlan.vid in self._cache_vlans.keys():
                logger.warn(f"{self.name} - Vlan {vlan.vid} already present in cache")

            self._cache_vlans[vlan.vid] = vlan

        return True


class NetworkImporterVlan(object):
    def __init__(self, name, vid):

        self.name = name
        self.vid = vid
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

