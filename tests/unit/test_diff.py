"""
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
from collections.abc import Iterable

from network_importer.diff import NetworkImporterDiff


def test_diff(diff_children_nyc_dev1):

    interfaces = NetworkImporterDiff.order_children_interface(children=diff_children_nyc_dev1)
    assert isinstance(interfaces, Iterable)

    interface_names = [intf.name for intf in interfaces]
    assert interface_names == ["eth2", "ae1", "ae0", "eth4", "eth0", "ae3", "eth1"]
