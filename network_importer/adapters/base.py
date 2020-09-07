from dsync import DSync


class BaseAdapter(DSync):
    def __init__(self, nornir):
        super().__init__()
        self.nornir = nornir

    def init(self):
        raise NotImplementedError

    def get_or_create_vlan(self, vlan, site=None):

        modelname = vlan.get_type()
        uid = vlan.get_unique_id()

        if uid in self.__datas__[modelname]:
            return self.__datas__[modelname][uid], False

        self.add(vlan)
        if site:
            site.add_child(vlan)

        return vlan, True
