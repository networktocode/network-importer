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

from typing import List


class BaseModel:
    """ """

    exclude_from_diff = []

    def get_attrs_diff(self) -> List[str]:
        """
        Return a list of Attributes of all the attributes of the class,
        Unless they should be explicitely excluded based on exclude_from_diff

        Return:
          List of attributes

        """
        attrs = list(vars(self).keys())
        for attr in self.exclude_from_diff:
            if attr in attrs:
                attrs.remove(attr)

        return sorted(attrs)


class Vlan(BaseModel):
    """
    Base class for Vlan
    In addition to the Name and Vlan ID
    This class also track a list of related devices which intent to represent on which device the vlan was found
    """

    exclude_from_diff = ["related_devices"]

    def __init__(self, name: str = None, vid=None, site: str = None):
        """

        Args:
          name: name of the vlan (Default value = None)
          vid: vlan id for the vlan, automatically converted to integer if provided (Default value = None)
          site: name of the site this vlan is associated with (Default value = None)

        Returns:
          None
        """
        self.name = name

        if vid:
            self.vid = int(vid)
        else:
            self.vid = None

        self.site = site
        self.related_devices = []


class Interface(BaseModel):
    """
    Base Class for Interface

    For now, speed has been excluded from the diff
    the goal is to add it back in the future
    """

    exclude_from_diff = ["lag_members", "speed"]

    def __init__(self, name: str = None):
        """

        Args:
          name:  (Default value = None)

        Returns:

        """
        self.name = name
        self.device_name = None
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


class IPAddress(BaseModel):
    """
    Base Class for IPaddress
    Current support only address
    """

    exclude_from_diff = ["family"]

    def __init__(self, address: str = None):
        """

        Args:
          address:  (Default value = None)

        Returns:

        """
        self.address = address
        self.family = None


class Prefix(BaseModel):
    """
    Base Class for Prefix
    """

    def __init__(self, prefix: str = None):
        """

        Args:
          prefix:  (Default value = None)
        """
        self.prefix = prefix
        self.family = None


class Optic(BaseModel):
    """
    Base Class for an optic
    """

    def __init__(
        self,
        name: str = None,
        optic_type: str = None,
        intf: str = None,
        serial: str = None,
    ):
        """

        Args:
          name:  (Default value = None)
          optic_type:  (Default value = None)
          intf:  (Default value = None)
          serial:  (Default value = None)

        Returns:

        """
        self.optic_type = optic_type
        self.intf = intf
        self.serial = serial
        self.name = name


class Cable(BaseModel):
    """
    Base Class for cable
    """

    exclude_from_diff = ["connections", "origin"]
    valid_sides = ["a", "z"]

    def __init__(self, origin=None):
        self.connections = {}
        self.unique_id = None
        self.origin = origin

    def get_device_intf(self, side):
        """
        Return the device name or the interface name of either side A or side Z of the cable
        """

        if side not in self.valid_sides:
            raise ValueError(
                f"{side} is not a valid parameter for get_side(), (supported: {self.valid_sides}"
            )

        if self.nbr_connections() != 2:
            return None, None

        return self.connections[side]["name"], self.connections[side]["interface"]

    def add_device(self, device, interface):

        side = None
        if "a" not in self.connections.keys():
            side = "a"
        elif "z" not in self.connections.keys():
            side = "z"
        else:
            raise Exception(
                f"Cable {self.unique_id}, Maximum number of connection already reached"
            )

        self.connections[side] = {
            "type": "device",
            "name": device,
            "interface": interface,
        }

        self.__update_unique_id()

    def __update_unique_id(self):

        if self.nbr_connections() == 2:
            self.unique_id = "_".join(
                sorted(
                    [
                        f"{self.connections['a']['name']}:{self.connections['a']['interface']}",
                        f"{self.connections['z']['name']}:{self.connections['z']['interface']}",
                    ]
                )
            )
        else:
            self.unique_id = None

    def nbr_connections(self):

        return len(self.connections.keys())
