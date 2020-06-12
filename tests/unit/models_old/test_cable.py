# pylint: disable=C0116,C0121,R0801

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

from network_importer.base_model import Cable
from network_importer.model import NetworkImporterCable


def test_network_importer_cable_diff():
    """ """

    nic = NetworkImporterCable()
    cable = Cable()
    cable.add_device("deva", "inta")
    cable.add_device("devb", "intb")
    nic.local = cable
    nic.remote = cable

    diff = nic.diff()
    assert diff.has_diffs() == False

    nic.remote = None
    diff = nic.diff()
    assert diff.has_diffs() == True


def test_base_model_cable_unique_id():
    """
    Unit test of base model Cable unique_id parameters
    """

    cable = Cable()
    cable.add_device("deva", "inta")
    cable.add_device("devb", "intb")

    assert cable.unique_id == "deva:inta_devb:intb"

    cable = Cable()
    cable.add_device("devb", "intb")
    cable.add_device("deva", "inta")

    assert cable.unique_id == "deva:inta_devb:intb"

    cable = Cable()
    cable.add_device("devb", "intb")

    assert cable.unique_id == None


def test_base_model_cable_get_device_intf():
    """
    Unit test of Cable get_device_intf function
    """

    cable = Cable()
    cable.add_device("deva", "inta")
    cable.add_device("devb", "intb")

    assert cable.get_device_intf("a") == ("deva", "inta")
    assert cable.get_device_intf("z") == ("devb", "intb")

    with pytest.raises(ValueError):
        cable.get_device_intf("v")
