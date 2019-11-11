from nornir.core.deserializer.inventory import Inventory, HostsDict

import os
from typing import Any, Dict, List, Optional, Union

import requests

class NornirInventoryFromBatfish(Inventory):
    """ 
    Construct a inventory object for Nornir based on the a list  NodesProperties from Batfish
    """
    def __init__(
        self,
        devices,
        **kwargs: Any,
    ) -> None:

        hosts = {}
        for dev in devices.itertuples():

            host: HostsDict = {"data": {}}
            host["hostname"] = dev.Hostname
            # host["data"]["vendor"] = str(dev.Vendor_Family).lower()
            host["data"]["type"] = str(dev.Device_Type).lower()
            
            hosts[dev.Hostname] = host

        super().__init__(hosts=hosts, groups={}, defaults={}, **kwargs)
