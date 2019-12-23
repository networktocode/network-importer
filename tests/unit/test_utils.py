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
from network_importer.utils import expand_vlans_list, sort_by_digits


def test_expand_vlans_list():

    assert expand_vlans_list("10-11") == [10, 11]
    assert expand_vlans_list("20-24") == [20, 21, 22, 23, 24]


def test_sort_by_digits():

    assert sort_by_digits("Eth0/2/3") == (0, 2, 3,)
    assert sort_by_digits("Eth0/2/543/14/6") == (0, 2, 543, 14, 6,)
    assert sort_by_digits("Eth0") == (0,)
    assert sort_by_digits("Eth") == ()
