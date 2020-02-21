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

from network_importer.model import NetworkImporterObjBase


def test_base_obj_passthrough_attribute():
    """
    Unit test of base model passthrough attributes capabilities
    """

    class Person:
        def __init__(self, firstname, lastname):
            self.firstname = firstname
            self.lastname = lastname

    # Local only
    mymodel = NetworkImporterObjBase()
    mymodel.local = Person("local_first", "local_last")
    assert mymodel.firstname == "local_first"
    assert mymodel.lastname == "local_last"

    # Remote only
    mymodel = NetworkImporterObjBase()
    mymodel.remote = Person("remote_first", "remote_last")
    assert mymodel.firstname == "remote_first"
    assert mymodel.lastname == "remote_last"

    # Both Remote and local
    mymodel = NetworkImporterObjBase()
    mymodel.remote = Person("remote_first", "remote_last")
    mymodel.local = Person("local_first", "local_last")
    assert mymodel.firstname == "local_first"
    assert mymodel.lastname == "local_last"

    # No attribute
    with pytest.raises(AttributeError):
        value = mymodel.notanattr
