from collections import defaultdict
from dsync.diff import Diff


class NetworkImporterDiff(Diff):
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
