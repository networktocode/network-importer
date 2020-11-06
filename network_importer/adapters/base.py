"""BaseAdapter for the network importer.

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
from diffsync import DiffSync
from network_importer.models import Site, Device, Interface, IPAddress, Cable, Vlan, Prefix


class BaseAdapter(DiffSync):
    """Base Adapter for the network importer."""

    site = Site
    device = Device
    interface = Interface
    ip_address = IPAddress
    cable = Cable
    vlan = Vlan
    prefix = Prefix

    def __init__(self, nornir, config):
        """Initialize the base adapter and store the nornir object locally."""
        super().__init__()
        self.nornir = nornir
        self.config = self._validate_config(config)

    @classmethod
    def _validate_config(cls, config):
        """Placeholder method that can be reimplemented by each adapter to validate if its config is valid."""
        return config

    def load(self):
        """Load the local cache with data from the remove system."""
        raise NotImplementedError

    def get_or_create_vlan(self, vlan, site=None):
        """Check if a vlan already exist before creating it. Returns the existing object if it already exist.

        Args:
            vlan (Vlan): Vlan object
            site (Site, optional): Site Object. Defaults to None.

        Returns:
            (Vlan, bool): return a tuple with the vlan and a bool to indicate of the vlan was created or not
        """
        modelname = vlan.get_type()
        uid = vlan.get_unique_id()

        if uid in self._data[modelname]:
            return self._data[modelname][uid], False

        self.add(vlan)
        if site:
            site.add_child(vlan)

        return vlan, True

    def get_or_add(self, obj):
        """Add a new object or retrieve it if it already exists.

        Args:
            obj (DiffSyncModel): DiffSyncModel oject

        Returns:
            DiffSyncModel: DiffSyncObject retrieved from the datastore
            Bool: True if the object was created
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        if uid in self._data[modelname]:
            return self._data[modelname][uid], False

        self.add(obj)

        return obj, True
