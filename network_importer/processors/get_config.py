"""GetConfig processor for the network_importer.

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
import os
import logging
from pathlib import Path

import hashlib

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

import network_importer.config as config
from network_importer.processors import BaseProcessor

LOGGER = logging.getLogger("network-importer")


class GetConfig(BaseProcessor):
    """GetConfig processor for the network_importer."""

    task_name = "get_config"
    config_extension = "txt"

    def __init__(self) -> None:
        """Initialize the processor and ensure some variables are properly initialized."""
        self.current_md5 = dict()
        self.previous_md5 = dict()
        self.config_filename = dict()
        self.config_dir = None
        self.existing_config_hostnames = None

    def task_started(self, task: Task) -> None:
        """Execute some house keeping item at the beginning at the execution.

        Before Update all the config file:
        - ensure that the configs directory exist
        - check what config files are already present

        Args:
            task (Task): Nornir Task
        """
        if not os.path.isdir(config.SETTINGS.main.configs_directory):
            os.mkdir(config.SETTINGS.main.configs_directory)
            LOGGER.debug("Configs directory created at %s", config.SETTINGS.main.configs_directory)

        self.config_dir = config.SETTINGS.main.configs_directory + "/configs"

        if not os.path.isdir(self.config_dir):
            os.mkdir(self.config_dir)
            LOGGER.debug("Configs directory created at %s", self.config_dir)

        # Save the hostnames associated with all existing configurations before we start the update process
        self.existing_config_hostnames = [
            f.split(f".{self.config_extension}")[0] for f in os.listdir(self.config_dir) if f.endswith(".txt")
        ]

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """At the end, remove all configs files that have not been updated."""
        if len(self.existing_config_hostnames) > 0:
            LOGGER.info("Will delete %s config(s) that have not been updated", len(self.existing_config_hostnames))

            for hostname in self.existing_config_hostnames:
                os.remove(os.path.join(self.config_dir, f"{hostname}.{self.config_extension}"))

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Before getting the new configuration, check if a configuration already exist and calculate its md5.

        Args:
            task (Task): Nornir Task
            host (Host): Nornir Host
        """
        if task.name != self.task_name:
            return

        self.config_filename[host.name] = f"{self.config_dir}/{task.host.name}.{self.config_extension}"

        if os.path.exists(self.config_filename[host.name]):
            current_config = Path(self.config_filename[host.name]).read_text()
            self.previous_md5[host.name] = hashlib.md5(current_config.encode("utf-8")).hexdigest()

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Verify the configuration returned and store it to disk.

        After collecting the configuration for each host.
        - Inspect the result and ensure the configuration is valid
        - If the configuration is valid, check the md5
        - if the MD5 is different, write the new configuration to disk

        Args:
            task (Task): Nornir Task
            host (Host): Nornir Host
            result (MultiResult): Nornir MultiResult
        """
        if task.name != self.task_name:
            return

        if result[0].failed:
            if result[0].exception:
                LOGGER.warning("%s | %s", task.host.name, result[0].exception)
            else:
                LOGGER.warning("%s | Something went wrong while trying to update the configuration ", task.host.name)
            host.status = "fail-other"
            return

        conf = result[0].result.get("config", None)

        if not conf:
            LOGGER.warning("%s | No configuration return ", task.host.name)
            host.status = "fail-other"
            return

        # Count the number of lines in the config file, if less than 10 report an error
        # mostlikely something went wrong while pulling the config
        if conf.count("\n") < 10:
            LOGGER.warning("%s | Less than 10 configuration lines returned", task.host.name)
            host.status = "fail-other"
            return

        if host.name in self.existing_config_hostnames:
            self.existing_config_hostnames.remove(host.name)

        # Save configuration to file and verify the new MD5
        with open(self.config_filename[host.name], "w") as config_:
            config_.write(conf)

        host.has_config = True

        self.current_md5[host.name] = hashlib.md5(conf.encode("utf-8")).hexdigest()
        # changed = False

        if host.name in self.previous_md5 and self.previous_md5[host.name] == self.current_md5[host.name]:
            LOGGER.info("%s | Latest config file already present ...", task.host.name)
        else:
            LOGGER.info("%s | Configuration file updated", task.host.name)
            # changed = True
