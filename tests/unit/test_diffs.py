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

import pytest
from network_importer.diff import NetworkImporterDiff, NetworkImporterDiffProp


def test_diff_prop_init():

    assert NetworkImporterDiffProp("test", 2, 2)
    assert NetworkImporterDiffProp("test", "string", "string")
    assert NetworkImporterDiffProp("test", [1], [1, 2])
    assert NetworkImporterDiffProp("test", dict(test=1), dict(test=2))

    with pytest.raises(ValueError):
        NetworkImporterDiffProp("test", dict(test=1), "string")

    with pytest.raises(ValueError):
        NetworkImporterDiffProp("test", 2, "2")


def test_diff_init():

    assert NetworkImporterDiff("interface", "test")

    with pytest.raises(ValueError):
        NetworkImporterDiff(2, "test")

    with pytest.raises(ValueError):
        NetworkImporterDiff("test", ["notastring"])
