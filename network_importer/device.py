

logger = logging.getLogger("network-importer")

class NetworkImporterDevice(object):

    def __init__(self, name, hostname=None, platform=None, model=None, role=None, bf=None, nb=None):

        self.name = name
        self.hostname = hostname
        self.platform = platform
        self.model = model
        self.role = role
        # State Machine to keep
        self.changed=False

        self.remote_id=None
        self.exist_remote=False

        self.interfaces = dict()
        self.hostvars = dict()

        #Batfish Object
        self.bf = bf
        self.nr = None

        # Netbox objects 
        #  Nb = Global pynetbox object 
        #  Remote = Device Object fro pynetbox 
        self.nb = nb
        self.remote = None

        self._cache_intfs = None
        self._cache_ips = None


    def add_interface(self, intf):
        """

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

        return true


    def _get_remote_interfaces_list(self):

        intfs = nb.dcim.interfaces.filter(device=self.name)

        if len(intfs) == 0:
            return True

        if self._cache_intfs == None:
            self._cache_intfs  = dict()

        for intf in intfs:
            if intf.name in self._cache_intfs.keys():
                logger.warn(f"{self.name} - Interface {intf.name} already present in cache, ")
            self._cache_intfs[intf.name] = intf

        return True


    def _get_remote_ips_list(self):
        self._cache_ips = nb.dcim.interfaces.filter(device=self.name)


class NetworkImporterInterface(object):

    def __init__(self, name, device_name):
        
        self.name = name
        self.device_name = device_name
        self.speed = None
        self.type = None
        self.remote_id = None

        self.exist_remote=False
        self.bf = None
        self.remote = None


class NetworkImporterSite(object):

    def __init__(self, name):
        
        self.name = name
        self.remote_id 


class NetworkImporterIP(object):

    def __init__(self, address):
        
        self.address = address
        self.family = None
        self.remote
