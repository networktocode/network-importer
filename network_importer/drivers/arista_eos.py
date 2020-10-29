"""network_importer driver for arista_eos.

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
import logging

from nornir.core.task import Result, Task

from network_importer.drivers.default import NetworkImporterDriver as DefaultNetworkImporterDriver
from network_importer.processors.get_vlans import Vlan, Vlans

LOGGER = logging.getLogger("network-importer")


class NetworkImporterDriver(DefaultNetworkImporterDriver):
    """Collection of Nornir Tasks specific to Arista EOS devices."""

    @staticmethod
    def get_vlans(task: Task) -> Result:
        """Get a list of vlans from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the vlans
            The format of the result but must be similar to Vlans defined in network_importer.processors.get_vlans
        """
        results = Vlans()

        nr_device = task.host.get_connection("napalm", task.nornir.config)
        eos_device = nr_device.device
        results = eos_device.run_commands(["show vlan"])

        if not isinstance(results[0], dict) or "vlans" not in results[0]:
            LOGGER.warning("%s | No vlans information returned", task.host.name)
            return Result(host=task.host, result=False)

        for vid, data in results[0]["vlans"].items():
            results.vlans.append(Vlan(name=data["name"], id=vid))

        return Result(host=task.host, result=results)
