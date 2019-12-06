
class NetworkImporterDiff(object):
    """
    Arguments:


    Attributes:

    """
    def __init__(self, obj_type, name):
        """

     
        """
        self.type = obj_type
        self.name = name
        self.items = {}
        self.childs = {}

    def add_item(self, name, local, remote):

        # TODO check if local and remote are of same type

        self.items[name] = NetworkImporterDiffProp(name, local, remote)
    
    def add_child(self, child):
        self.childs[child.name] = child

    def nbr_diffs(self):
        return len(self.items.keys())

    def has_diffs(self):

        status = False

        if len(self.items.keys()):
            status = True

        for child in self.childs.values():
            if child.has_diffs():
                status = True

        return status

    def print_detailed(self, indent=0):

        margin = " "*indent

        print(f"{margin}{self.type}: {self.name}")
        for item in self.items.values():
            print(f"{margin}  {item.name}   L({item.local})   R({item.remote})")

        if len(self.childs) == 0:
            return True
            
        print(f"{margin}  Childs")
        for child in self.childs.values():
            if len(child.items):
                child.print_detailed(indent=indent+4)



            
class NetworkImporterDiffProp(object):

    def __init__(self, name, local, remote):

        self.name = name
        self.local = local
        self.remote = remote


    