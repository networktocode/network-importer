from diffsync import DiffSync


class BaseAdapter(DiffSync):
    def __init__(self, nornir):
        super().__init__()
        self.nornir = nornir

    def load(self):
        raise NotImplementedError

    def get_or_create_vlan(self, vlan, site=None):

        modelname = vlan.get_type()
        uid = vlan.get_unique_id()

        if uid in self._data[modelname]:
            return self._data[modelname][uid], False

        self.add(vlan)
        if site:
            site.add_child(vlan)

        return vlan, True

    def get_or_add(self, obj):
        """Add a new object or retrieve it if it already exists

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
