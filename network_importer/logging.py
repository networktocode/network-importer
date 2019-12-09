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

import json
import math
from time import strftime, time
import network_importer.config as config


def changelog_create(obj_type, obj_name, obj_id, params):
    cl = ChangelogCreate(
        obj_type=obj_type, obj_id=obj_id, obj_name=obj_name, params=params
    )
    cl.print()


def changelog_update(obj_type, obj_name, obj_id, params):
    cl = ChangelogUpdate(
        obj_type=obj_type, obj_id=obj_id, obj_name=obj_name, params=params
    )
    cl.print()


def changelog_delete(obj_type, obj_name, obj_id):
    cl = ChangelogDelete(obj_type=obj_type, obj_id=obj_id, obj_name=obj_name)
    cl.print()


class Changelog(object):
    obj_type = None
    obj_name = None
    obj_id = None
    params = None

    def __init__(self, obj_type, obj_id, obj_name, params=None):
        self.obj_id = obj_id
        self.obj_name = obj_name
        self.obj_type = obj_type
        self.params = params

    def print(self):

        if not config.logs["change_log"]:
            return True

        if config.logs["change_log_format"] == "jsonlines":
            self.print_jsonlines()
        elif config.logs["change_log_format"] == "text":
            self.print_text()

    def print_jsonlines(self):
        jcl = {
            "timestamp": int(time() * 1000),
            "time": strftime("%Y-%m-%d %H:%M:%S"),
            "action": self.log_type,
            "object": {
                "id": self.obj_id,
                "name": self.obj_name,
                "type": self.obj_type,
            },
            "params": self.params,
        }

        with open(config.logs["change_log_filename"] + ".jsonl", "a") as f:
            f.write(json.dumps(jcl) + "\n")

    def print_text(self):

        log = "{time} {action} {obj_type} {obj_name} ({obj_id}) {params}".format(
            time=strftime("%Y-%m-%d %H:%M:%S"),
            action=self.log_type,
            obj_id=self.obj_id,
            obj_name=self.obj_name,
            obj_type=self.obj_type,
            params=self.params,
        )

        with open(config.logs["change_log_filename"] + ".log", "a") as f:
            f.write(log + "\n")


class ChangelogCreate(Changelog):
    log_type = "create"


class ChangelogUpdate(Changelog):
    log_type = "update"


class ChangelogDelete(Changelog):
    log_type = "delete"
