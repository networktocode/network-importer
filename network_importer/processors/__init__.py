import logging
from typing import Dict

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task

logger = logging.getLogger("network-importer")


class BaseProcessor:

    task_name = "'no task defined'"

    def task_started(self, task: Task) -> None:
        pass

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        pass

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        pass

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        pass
