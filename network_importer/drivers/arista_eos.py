import logging

from nornir.core.task import Result, Task

from network_importer.drivers.default import NetworkImporterDriver as DefaultNetworkImporterDriver
from network_importer.processors.get_vlans import Vlan, Vlans

LOGGER = logging.getLogger("network-importer")


class NetworkImporterDriver(DefaultNetworkImporterDriver):
    """Collection of Nornir Tasks specific to Arista EOS devices."""

    @staticmethod
    def get_vlans(task: Task):

        results = Vlans()

        nr_device = task.host.get_connection("napalm", task.nornir.config)
        eos_device = nr_device.device
        results = eos_device.run_commands(["show vlan"])

        if not isinstance(results[0], dict) or not "vlans" in results[0]:
            LOGGER.warning(f"{task.host.name} | No vlans information returned")
            return Result(host=task.host, result=False)

        for vid, data in results[0]["vlans"].items():
            results.vlans.append(Vlan(name=data["name"], id=vid))
