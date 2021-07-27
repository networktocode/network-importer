"""BaseAdapter for the network importer."""
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

    settings_class = None
    settings = None

    def __init__(self, nornir, settings):
        """Initialize the base adapter and store the Nornir object locally."""
        super().__init__()
        self.nornir = nornir
        self.settings = self._validate_settings(settings)

    def _validate_settings(self, settings):
        """Load and validate the configuration based on the settings_class."""
        if self.settings_class:
            if settings and isinstance(settings, dict):
                return self.settings_class(**settings)  # pylint: disable=not-callable

            return self.settings_class()  # pylint: disable=not-callable

        return settings

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
