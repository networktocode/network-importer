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

from network_importer.base_model import Interface, IPAddress, Prefix, Optic, Vlan, Cable
import network_importer.config as config

logger = logging.getLogger("network-importer")  # pylint: disable=C0103


class NetboxInterface(Interface):
    """ """

    def __init__(self, **kargs):
        """ """
        super().__init__(**kargs)
        self.remote = None

    def add(self, rem):
        """ """
        raise NotImplementedError

    def update(self, rem):
        """ """

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

        self.add(rem)

    def delete(self):
        """ """
        self.remote.delete()
        return True


class Netbox26Interface(NetboxInterface):
    def add(self, rem):
        """ """

        self.remote = rem
        self.name = rem.name

        if config.main["import_intf_status"]:
            self.active = rem.enabled
        else:
            self.active = None

        self.description = rem.description

        if rem.type.value == 200:
            self.is_lag = True
            self.is_virtual = False
        elif rem.type.value == 0:
            self.is_virtual = True
            self.is_lag = False
        else:
            self.is_lag = False
            self.is_virtual = False

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

    @staticmethod
    def get_properties(intf):
        """
        Get a dict with all interface properties in Netbox format

        Input: Vlan
        Output: Dictionnary of properties ready to pass to netbox
        minus the vlans IDs that needs to be converted

        Args:
        intf:

        Returns:

        """

        intf_properties = dict()

        if intf.is_lag:
            intf_properties["type"] = 200
        elif intf.is_virtual:
            intf_properties["type"] = 0
        else:
            intf_properties["type"] = 32767

        if intf.mtu:
            intf_properties["mtu"] = intf.mtu

        if intf.description is not None:
            intf_properties["description"] = intf.description

        # TODO Add a check here to see what is the current status
        if intf.switchport_mode == "ACCESS":
            intf_properties["mode"] = 100
        elif intf.switchport_mode == "TRUNK":
            intf_properties["mode"] = 200
        else:
            intf_properties["mode"] = None

        if not intf.active is None:
            intf_properties["enabled"] = intf.active

        return intf_properties


class Netbox27Interface(NetboxInterface):
    def add(self, rem):
        """ """

        self.remote = rem
        self.name = rem.name

        if config.main["import_intf_status"]:
            self.active = rem.enabled
        else:
            self.active = None

        self.description = rem.description

        if rem.type and rem.type.value == "lag":
            self.is_lag = True
            self.is_virtual = False
        elif rem.type and rem.type.value == "virtual":
            self.is_virtual = True
            self.is_lag = False
        else:
            self.is_lag = False
            self.is_virtual = False

        if rem.lag:
            self.is_lag_member = True
            self.is_lag = False
            self.is_virtual = False
            self.parent = rem.lag.name

        if rem.mode and rem.mode.value == "access":
            self.switchport_mode = "ACCESS"
            self.mode = self.switchport_mode
        elif rem.mode and rem.mode.value == "tagged":
            self.switchport_mode = "TRUNK"
            self.mode = self.switchport_mode
        else:
            self.switchport_mode = "NONE"
            self.mode = "NONE"

        if rem.type and rem.type.value == 800:
            self.speed = 1000000000
        elif rem.type and rem.type.value == 1100:
            self.speed = 1000000000
        elif rem.type and rem.type.value == 1200:
            self.speed = 10000000000
        elif rem.type and rem.type.value == 1350:
            self.speed = 25000000000
        elif rem.type and rem.type.value == 1400:
            self.speed = 40000000000
        elif rem.type and rem.type.value == 1600:
            self.speed = 100000000000

        if rem.tagged_vlans:
            self.allowed_vlans = [v.vid for v in rem.tagged_vlans]

        if rem.untagged_vlan:
            self.access_vlan = rem.untagged_vlan.vid

        return True

    @staticmethod
    def get_properties(intf):
        """
        Get a dict with all interface properties in Netbox format

        Input: Vlan
        Output: Dictionnary of properties ready to pass to netbox
        minus the vlans IDs that needs to be converted

        Args:
        intf:

        Returns:

        """

        intf_properties = dict()

        if intf.is_lag:
            intf_properties["type"] = "lag"
        elif intf.is_virtual:
            intf_properties["type"] = "virtual"
        else:
            intf_properties["type"] = "other"

        if intf.mtu:
            intf_properties["mtu"] = intf.mtu

        if intf.description is not None:
            intf_properties["description"] = intf.description

        # TODO Add a check here to see what is the current status
        if intf.switchport_mode == "ACCESS":
            intf_properties["mode"] = "access"
        elif intf.switchport_mode == "TRUNK":
            intf_properties["mode"] = "tagged"

        if not intf.active is None:
            intf_properties["enabled"] = intf.active

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


class NetboxIPAddress(IPAddress):
    """ """

    def __init__(self, **kargs):
        """ """
        super().__init__(**kargs)
        self.remote = None

    def add(self, rem):
        """ """
        self.address = rem.address
        self.family = rem.family
        self.remote = rem

    def update(self, rem):
        """ """
        self.add(rem)

    def delete(self):
        """
        Remote delete IP address
        """
        self.remote.delete()
        return True


class NetboxPrefix(Prefix):
    """ """

    def __init__(self, **kargs):
        """ """
        super().__init__(**kargs)
        self.remote = None

    def add(self, rem):
        """ """
        self.prefix = rem.prefix
        self.remote = rem

    def update(self, rem):
        """ """
        self.add(rem)

    def delete(self):
        """
        Remote delete Prefix
        """
        self.remote.delete()
        return True


class NetboxOptic(Optic):
    """ """

    def __init__(self, **kargs):
        """ """
        super().__init__(**kargs)
        self.remote = None

    def add(self, rem):
        """ """
        self.optic_type = rem.part_id
        self.intf = rem.description
        self.serial = rem.serial
        self.name = rem.serial
        self.remote = rem

    def update(self, rem):
        """ """
        self.add(rem)

    def delete(self):
        """

        Args:

        Returns:
          True when delete is complete

        """
        self.remote.delete()
        return True


class NetboxVlan(Vlan):
    """ """

    def __init__(self, **kargs):
        """ """
        super().__init__(**kargs)
        self.remote = None

    def add(self, rem):
        """ """
        self.vid = rem.vid
        self.name = rem.name

        for tag in rem.tags:
            if "device=" not in tag:
                continue
            tag_type, dev_name = tag.split("=", 1)
            self.related_devices.append(dev_name)

        self.remote = rem

    def update(self, rem):
        """ """
        self.add(rem)

    def delete(self):
        """

        Args:

        Returns:
            True when delete of remote VLAN complete

        """
        self.remote.delete()
        return True


class NetboxCable(Cable):
    def __init__(self, **kargs):
        """ """
        super().__init__(**kargs)
        self.remote = None

    def add(self, cable=None, interface=None):
        """ """

        if interface:
            self.remote = interface.cable
            self.add_device(
                interface.connected_endpoint.device.name,
                interface.connected_endpoint.name,
            )
            self.add_device(interface.device.name, interface.name)

        elif cable:
            self.remote = cable

    def update(self, cable=None, interface=None):
        """ """
        self.add(cable=cable, interface=interface)

    def delete(self):
        """ """
        self.remote.delete()
