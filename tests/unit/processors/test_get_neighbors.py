"""unit test for get_neighbors processor.

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
from os import path
import yaml

import pytest

from nornir import InitNornir
from nornir.core.task import Task, Result

import network_importer.config as config
from network_importer.processors.get_neighbors import GetNeighbors, Neighbor, Neighbors

HERE = path.abspath(path.dirname(__file__))
FIXTURES = "../fixtures/inventory"

# pylint: disable=redefined-outer-name


@pytest.fixture()
def nornir(requests_mock):
    """pytest fixture to return a nornir inventory based on mock data."""

    data1 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/devices.json"))
    requests_mock.get("http://mock/api/dcim/devices/?exclude=config_context", json=data1)

    data2 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/platforms.json"))
    requests_mock.get("http://mock/api/dcim/platforms/", json=data2)

    nornir = InitNornir(
        runner={"plugin": "threaded", "options": {"num_workers": 1}},
        logging={"enabled": False},
        inventory={
            "plugin": "NetboxAPIInventory",
            "options": {"settings": {"address": "http://mock", "token": "12349askdnfanasdf"}},
        },
    )

    return nornir


def get_neighbors(task: Task, neighbors) -> Result:
    """Test task to validate the neighbors."""
    results = Neighbors(**neighbors)
    return Result(host=task.host, result=results.dict())


def dispatch_get_neighbors(task, **kwargs):
    """Dummy Class to emulate the dispatcher."""
    result = task.run(task=get_neighbors, **kwargs)
    return Result(host=task.host, result=result)


def test_base(nornir):
    """Validate that the processor is working as expected with standard inputs."""
    config.load()

    neighbors = Neighbors()
    neighbors.neighbors["intfa"].append(Neighbor(hostname="devicea", port="intfa"))
    neighbors.neighbors["intfb"].append(Neighbor(hostname="deviceb", port="intfa"))

    results = (
        nornir.filter(name="houston")
        .with_processors([GetNeighbors()])
        .run(task=dispatch_get_neighbors, neighbors=neighbors.dict())
    )

    result = results["houston"][0].result[0].result
    assert "neighbors" in result
    assert "intfa" in result["neighbors"]


def test_cleanup_fqdn(nornir):
    """Validate that we are cleaning up the FQDN from device name."""
    config.load(config_data={"network": {"fqdns": ["test.com"]}})

    neighbors = Neighbors()
    neighbors.neighbors["intfa"].append(Neighbor(hostname="devicea.test.com", port="intfa"))
    neighbors.neighbors["intfb"].append(Neighbor(hostname="deviceb", port="intfa"))

    results = (
        nornir.filter(name="houston")
        .with_processors([GetNeighbors()])
        .run(task=dispatch_get_neighbors, neighbors=neighbors.dict())
    )

    result = results["houston"][0].result[0].result
    assert "neighbors" in result
    assert result["neighbors"]["intfa"][0]["hostname"] == "devicea"


def test_cleanup_mac_address(nornir):
    """Validate that we are removing neighbor with a mac address name."""
    config.load(config_data={"network": {"fqdns": ["test.com"]}})

    neighbors = Neighbors()
    neighbors.neighbors["intfa"].append(Neighbor(hostname="devicea.test.com", port="intfa"))
    neighbors.neighbors["intfb"].append(Neighbor(hostname="f8:f2:1e:89:3c:61", port="intfa"))

    results = (
        nornir.filter(name="houston")
        .with_processors([GetNeighbors()])
        .run(task=dispatch_get_neighbors, neighbors=neighbors.dict())
    )

    result = results["houston"][0].result[0].result
    assert "neighbors" in result
    assert "intfb" not in result["neighbors"]


def test_cleanup_port(nornir):
    """Validate that we are cleaning up the port from port name."""
    config.load(config_data={"network": {"fqdns": ["test.com"]}})

    neighbors = Neighbors()
    neighbors.neighbors["intfa"].append(Neighbor(hostname="devicea", port="HundredGigE0/0/0/0"))
    neighbors.neighbors["intfb"].append(Neighbor(hostname="deviceb", port="TenGigE0/0/0/35/3"))
    neighbors.neighbors["intfc"].append(Neighbor(hostname="devicec", port="Xe-0/1/2"))
    neighbors.neighbors["intfd"].append(Neighbor(hostname="deviced", port="Ge-0/1/3.400"))
    neighbors.neighbors["intfe"].append(Neighbor(hostname="devicee", port="Eth2/10"))
    neighbors.neighbors["intff"].append(Neighbor(hostname="deviced", port="Xle-0/1/3:400"))

    results = (
        nornir.filter(name="houston")
        .with_processors([GetNeighbors()])
        .run(task=dispatch_get_neighbors, neighbors=neighbors.dict())
    )

    result = results["houston"][0].result[0].result
    assert "neighbors" in result
    assert result["neighbors"]["intfa"][0]["port"] == "HundredGigE0/0/0/0"
    assert result["neighbors"]["intfb"][0]["port"] == "TenGigE0/0/0/35/3"
    assert result["neighbors"]["intfc"][0]["port"] == "xe-0/1/2"
    assert result["neighbors"]["intfd"][0]["port"] == "ge-0/1/3.400"
    assert result["neighbors"]["intfe"][0]["port"] == "Eth2/10"
    assert result["neighbors"]["intff"][0]["port"] == "xle-0/1/3:400"
