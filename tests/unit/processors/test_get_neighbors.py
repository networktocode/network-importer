from os import path
import yaml

import pytest

from nornir import InitNornir
from nornir.core.task import MultiResult, Task, Result

import network_importer.config as config
from network_importer.processors.get_neighbors import GetNeighbors, Neighbor, Neighbors

HERE = path.abspath(path.dirname(__file__))
FIXTURES = "../config/fixtures/NBInventory"


@pytest.fixture()
def nornir(requests_mock):

    # Load mock data fixtures
    data1 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/devices.json"))
    requests_mock.get("http://mock/api/dcim/devices/?exclude=config_context", json=data1)

    data2 = yaml.safe_load(open(f"{HERE}/{FIXTURES}/platforms.json"))
    requests_mock.get("http://mock/api/dcim/platforms/", json=data2)

    nornir = InitNornir(
        core={"num_workers": 1},
        logging={"enabled": False},
        inventory={
            "plugin": "network_importer.inventory.NetboxInventory",
            "options": {"nb_url": "http://mock", "nb_token": "12349askdnfanasdf",},
        },
    )

    return nornir


def get_neighbors(task: Task, neighbors) -> Result:
    results = Neighbors(**neighbors)
    return Result(host=task.host, result=results.dict())


def dispatch_get_neighbors(task, **kwargs):
    """Dummy Class to emulate the dispatcher."""
    result = task.run(task=get_neighbors, **kwargs)
    return Result(host=task.host, result=result)


def test_base(nornir):

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
    config.load(config_data={"main": {"fqdn": "test.com"}})

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
    config.load(config_data={"main": {"fqdn": "test.com"}})

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
