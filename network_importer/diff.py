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
        self.missing_remote = None
        self.missing_local = None

    def __str__(self):

        if self.missing_remote and self.missing_local:
            return f"{self.type}:{self.name} MISSING BOTH"
        elif self.missing_remote:
            return f"{self.type}:{self.name} MISSING REMOTE"
        elif self.missing_local:
            return f"{self.type}:{self.name} MISSING LOCAL"
        elif not self.has_diffs():
            return f"{self.type}:{self.name} NO DIFF"
        else:
            return f"{self.type}:{self.name} {self.nbr_diffs()} DIFFs"

    def add_item(self, name, local, remote):

        # TODO check if local and remote are of same type

        self.items[name] = NetworkImporterDiffProp(name, local, remote)

    def add_child(self, child):
        self.childs[child.name] = child

    def nbr_diffs(self):
        return len(self.items.keys())

    def has_diffs(self, include_childs=True):

        status = False

        if len(self.items.keys()):
            status = True

        if self.missing_remote or self.missing_local:
            status = True

        if not include_childs:
            return status

        for child in self.childs.values():
            if child.has_diffs():
                status = True

        return status

    def print_detailed(self, indent=0):

        margin = " " * indent

        if self.missing_remote and self.missing_local:
            print(f"{margin}{self.type}: {self.name} MISSING BOTH")
        elif self.missing_remote:
            print(f"{margin}{self.type}: {self.name} MISSING REMOTE")
        elif self.missing_local:
            print(f"{margin}{self.type}: {self.name} MISSING LOCAL")
        else:
            print(f"{margin}{self.type}: {self.name}")
            for item in self.items.values():
                print(f"{margin}  {item.name}   L({item.local})   R({item.remote})")

        if len(self.childs) == 0:
            return True

        print(f"{margin}  Childs")
        for child in self.childs.values():
            if child.has_diffs():
                child.print_detailed(indent=indent + 4)

    def items_to_dict(self):

        items = {} 
        for item in self.items.values():
            items[item.name] = item.local

        return items 

class NetworkImporterDiffProp(object):
    def __init__(self, name, local, remote):

        self.name = name
        self.local = local
        self.remote = remote
