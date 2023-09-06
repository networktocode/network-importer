"""Unit tests for NetworkImporterDiff."""
from collections.abc import Iterable

from network_importer.diff import NetworkImporterDiff


def test_diff(diff_children_nyc_dev1):
    interfaces = NetworkImporterDiff.order_children_interface(children=diff_children_nyc_dev1)
    assert isinstance(interfaces, Iterable)

    interface_names = [intf.name for intf in interfaces]
    assert interface_names == ["eth2", "ae1", "ae0", "eth4", "eth0", "ae3", "eth1"]
