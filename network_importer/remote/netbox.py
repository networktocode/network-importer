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

from network_importer.base_model import Interface, IPAddress, Optic, Vlan


def get_netbox_interface_properties(intf):
    """
    Get a dict with all interface properties in Netbox format 

    Input: Vlan
    Output: Dictionnary of properties ready to pass to netbox
    minus the vlans IDs that needs to be converted
    """

    intf_properties = dict()

    if intf.is_lag:
        intf_properties["type"] = 200
    elif intf.is_virtual:
        intf_properties["type"] = 0
    elif intf.speed == 1000000000:
        intf_properties["type"] = 800
    elif intf.speed == 1000000000:
        intf_properties["type"] = 1100
    elif intf.speed == 10000000000:
        intf_properties["type"] = 1200
    elif intf.speed == 25000000000:
        intf_properties["type"] = 1350
    elif intf.speed == 40000000000:
        intf_properties["type"] = 1400
    elif intf.speed == 100000000000:
        intf_properties["type"] = 1600
    else:
        intf_properties["type"] = 1100

    if intf.mtu:
        intf_properties["mtu"] = intf.mtu

    if intf.description is not None:
        intf_properties["description"] = intf.description

    # TODO Add a check here to see what is the current status
    if intf.switchport_mode == "ACCESS":
        intf_properties["mode"] = 100

    elif intf.switchport_mode == "TRUNK":
        intf_properties["mode"] = 200

    if not intf.active is None:
        intf_properties["enabled"] = intf.active

    return intf_properties


class InterfaceRemote(Interface):
    def __init__(self):
        super()
        self.remote = None

    def add_remote_info(self, rem):

        self.remote = rem

        self.name = rem.name

        self.active = rem.enabled

        self.description = rem.description

        if rem.type.value == 200:
            self.is_lag = True
            self.is_virtual = False
        elif rem.type.value == 0:
            self.is_virtual = True
            self.is_lag = False
        else:
            self.is_lag = False

        if rem.lag:
            self.is_lag_member = True
            self.is_lag = False
            self.is_virtual = False
            self.parent = rem.lag.name

        if rem.mode and rem.mode.value == 100:
            self.switchport_mode = "ACCESS"
            self.mode = self.switchport_mode
        elif rem.mode and rem.mode.value == 200:
            self.switchport_mode = "TRUNK"
            self.mode = self.switchport_mode
        else:
            self.switchport_mode = "NONE"
            self.mode = "NONE"

        if rem.type.value == 800:
            self.speed = 1000000000
        elif rem.type.value == 1100:
            self.speed = 1000000000
        elif rem.type.value == 1200:
            self.speed = 10000000000
        elif rem.type.value == 1350:
            self.speed = 25000000000
        elif rem.type.value == 1400:
            self.speed = 40000000000
        elif rem.type.value == 1600:
            self.speed = 100000000000

        if rem.tagged_vlans:
            self.allowed_vlans = [v.vid for v in rem.tagged_vlans]

        if rem.untagged_vlan:
            self.access_vlan = rem.untagged_vlan.vid

        return True

    def update_remote_info(self, rem):

        # Clear all existing info first
        self.mode = None  # TRUNK, ACCESS, L3, NONE
        self.is_virtual = None
        self.active = None
        self.is_lag_member = None
        self.parent = None
        self.is_lag = None
        self.lag_members = None

        self.description = None
        self.speed = None
        self.mtu = None
        self.switchport_mode = None  # = None
        self.access_vlan = None
        self.allowed_vlans = None

        self.add_remote_info(rem)

    def delete(self):
        self.remote.delete()
        return True


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


class IPAddressRemote(IPAddress):
    def __init__(self):
        super()
        self.remote = None

    def add_remote_info(self, rem):
        self.address = rem.address
        self.family = rem.family
        self.remote = rem

    def update_remote_info(self, rem):
        self.add_remote_info(rem)

    def delete(self):
        self.remote.delete()
        return True


class OpticRemote(Optic):
    def __init__(self):
        super()
        self.remote = None

    def add_remote_info(self, rem):
        self.optic_type = rem.part_id
        self.intf = rem.description
        self.serial = rem.serial
        self.name = rem.serial
        self.remote = rem

    def update_remote_info(self, rem):
        self.add_remote_info(rem)

    def delete(self):
        self.remote.delete()
        return True


class VlanRemote(Vlan):
    def __init__(self):
        super()
        self.remote = None

    def add_remote_info(self, rem):

        self.vid = rem.vid
        self.name = rem.name
        self.remote = rem

    def update_remote_info(self, rem):
        self.add_remote_info(rem)

    def delete(self):
        self.remote.delete()
        return True
