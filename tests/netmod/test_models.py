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
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Table,
    ForeignKeyConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

from netmod.models import BaseNetMod


class Person(Base, BaseNetMod):

    __tablename__ = "person"

    diffs = ["name"]
    attributes = ["age", "size"]

    first = Column(String(20), primary_key=True)
    last = Column(String(20), primary_key=True)
    middle = Column(String(20), primary_key=True)
    age = Column(Integer)
    size = Column(Integer)


def test_basenetmod_get_keys():

    person = Person(first="john", last="doe", middle="bob", age=99, size=120)

    keys = person.get_keys()
    assert isinstance(keys, dict)
    assert len(keys.keys()) == 3
    assert keys["first"] == "john"


def test_basenetmod_get_attrs():

    person = Person(first="john", last="doe", middle="bob", age=99, size=120)

    attrs = person.get_attrs()
    assert isinstance(attrs, dict)
    assert len(attrs.keys()) == 2
    assert attrs["age"] == 99
