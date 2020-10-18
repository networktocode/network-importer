# pylint: disable=C0116,C0121,R0801

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
import pytest

from network_importer.models import Cable


def test_get_unique_id():
    """
    Unit test of Calbe model get_unique_id() parameters
    """

    cable = Cable(device_a_name="deva", interface_a_name="inta", device_z_name="devb", interface_z_name="intb")
    assert cable.get_unique_id() == "deva:inta__devb:intb"

    cable = Cable(device_z_name="deva", interface_z_name="inta", device_a_name="devb", interface_a_name="intb")
    assert cable.get_unique_id() == "deva:inta__devb:intb"


def test_get_device_intf():
    """
    Unit test of Cable get_device_intf function
    """

    cable = Cable(device_a_name="deva", interface_a_name="inta", device_z_name="devb", interface_z_name="intb")
    assert cable.get_device_intf("a") == ("deva", "inta")
    assert cable.get_device_intf("z") == ("devb", "intb")

    with pytest.raises(ValueError):
        cable.get_device_intf("v")
