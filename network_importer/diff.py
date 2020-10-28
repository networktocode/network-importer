"""network_importer specific diff class based on diffsync.

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
from collections import defaultdict
from diffsync.diff import Diff


class NetworkImporterDiff(Diff):
    """network_importer specific diff class based on diffsync."""

    @classmethod
    def order_children_interface(cls, children):
        """Return the interface children ordered order."""
        intfs_lags = defaultdict(list)
        intfs_regs = defaultdict(list)
        intfs_lag_members = defaultdict(list)

        for child_name, child in children.items():
            action = child.action

            if action is None:
                action = "update"

            if action == "delete":
                if "is_lag" in child.dest_attrs and child.dest_attrs["is_lag"]:
                    intfs_lags[action].append(child_name)
                elif "is_lag_member" in child.dest_attrs and child.dest_attrs["is_lag_member"]:
                    intfs_lag_members[action].append(child_name)
                else:
                    intfs_regs[action].append(child_name)

            elif action in ["update", "create"]:

                if "is_lag" in child.source_attrs and child.source_attrs["is_lag"]:
                    intfs_lags[action].append(child_name)
                elif "is_lag_member" in child.source_attrs and child.source_attrs["is_lag_member"]:
                    intfs_lag_members[action].append(child_name)
                else:
                    intfs_regs[action].append(child_name)

            else:
                raise Exception("invalid DiffElement")

        sorted_intfs = intfs_regs["create"]
        sorted_intfs += intfs_regs["update"]
        sorted_intfs += intfs_lags["create"]
        sorted_intfs += intfs_lags["update"]
        sorted_intfs += intfs_lag_members["create"]
        sorted_intfs += intfs_lag_members["update"]
        sorted_intfs += intfs_regs["delete"]
        sorted_intfs += intfs_lags["delete"]
        sorted_intfs += intfs_lag_members["delete"]

        for intf in sorted_intfs:
            yield children[intf]
