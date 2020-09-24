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

    task_name = "get_config"
    config_extension = "txt"

    def __init__(self) -> None:
        self.current_md5 = dict()
        self.previous_md5 = dict()
        self.config_filename = dict()
        self.config_dir = None
        self.existing_config_hostnames = None

    def task_started(self, task: Task) -> None:
        """Before Update all the config file:
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
        """At the end, remove all configs files that have not been updated
        to ensure that we are loading just the right config files in Batfish
        """

        if len(self.existing_config_hostnames) > 0:
            LOGGER.info("Will delete %s config(s) that have not been updated", len(self.existing_config_hostnames))

            for hostname in self.existing_config_hostnames:
                os.remove(os.path.join(self.config_dir, f"{hostname}.{self.config_extension}"))

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Before getting the new configuration, check if a configuration already exist and calculate it's md5

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

        if task.name != self.task_name:
            return

        if result[0].failed:
            LOGGER.warning("%s | Something went wrong while trying to update the configuration ", task.host.name)
            host.data["status"] = "fail-other"
            return

        conf = result[0].result.get("config", None)

        if not conf:
            LOGGER.warning("%s | No configuration return ", task.host.name)
            host.data["status"] = "fail-other"
            return

        if host.name in self.existing_config_hostnames:
            self.existing_config_hostnames.remove(host.name)

        # Save configuration to to file and verify the new MD5
        with open(self.config_filename[host.name], "w") as config_:
            config_.write(conf)

        self.current_md5[host.name] = hashlib.md5(conf.encode("utf-8")).hexdigest()
        changed = False

        if host.name in self.previous_md5 and self.previous_md5[host.name] == self.current_md5[host.name]:
            LOGGER.debug("%s | Latest config file already present ...", task.host.name)
        else:
            LOGGER.info("%s | Configuration file updated", task.host.name)
            changed = True
