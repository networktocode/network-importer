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

from network_importer.base_model import BaseModel
from network_importer.model import NetworkImporterObjBase


def test_base_model_init():
    """
    Functional test of base model initilization
    """

    class MyModel(BaseModel):
        """
        Test Model definition
        """

        exclude_from_diff = ["firstname"]

        def __init__(self):
            self.firstname = "firstname"
            self.lastname = "lastname"

    assert MyModel()

    mymodel = MyModel()
    assert mymodel.get_attrs_diff() == ["lastname"]
