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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column,
    Integer
)
from network_importer.models import Site, Device, Interface, IPAddress, Cable

Base = declarative_base()

class NetboxSite(Site):
    remote_id = Column(Integer, nullable=True)

class NetboxDevice(Device):
    remote_id = Column(Integer, nullable=True)

class NetboxInterface(Interface):
    remote_id = Column(Integer, nullable=True)
    
class NetboxIPAddress(IPAddress):
    remote_id = Column(Integer, nullable=True)

class NetboxCable(Cable):
    remote_id = Column(Integer, nullable=True)
    termination_a_id = Column(Integer, nullable=True)
    termination_z_id = Column(Integer, nullable=True)
