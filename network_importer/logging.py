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
from time import strftime, time
import network_importer.config as config


def changelog_create(obj_type, obj_name, obj_id, params):
    """
    Args:
      obj_type:
      obj_name:
      obj_id:

    Returns:

    """
    changelog = ChangelogCreate(obj_type=obj_type, obj_id=obj_id, obj_name=obj_name, params=params)
    changelog.save()


def changelog_update(obj_type, obj_name, obj_id, params):
    """

    Args:
      obj_type:
      obj_name:
      obj_id:
      params:

    Returns:


    """
    changelog = ChangelogUpdate(obj_type=obj_type, obj_id=obj_id, obj_name=obj_name, params=params)
    changelog.save()


def changelog_delete(obj_type, obj_name, obj_id):
    """

    Args:
      obj_type:
      obj_name:
      obj_id:

    Returns:

    """
    changelog = ChangelogDelete(obj_type=obj_type, obj_id=obj_id, obj_name=obj_name)
    changelog.save()


class Changelog:
    """
    Base Changelog object to track a specific changes done on the remote system.
    A changelog is defined by an Id a type and a name. It can also includes additional parameters
    """

    def __init__(self, obj_type, obj_id, obj_name, params=None):
        """


        Args:
          obj_type:
          obj_id:
          obj_name:
          params:  (Default value = None)

        Returns:

        """

        # ------------------------------------------------------------------------------------------
        # TODO: Add definition for self.log_type
        # ------------------------------------------------------------------------------------------
        self.obj_id = obj_id
        self.obj_name = obj_name
        self.obj_type = obj_type
        self.params = params

    def save(self):
        """
        Save the changelog, the destination is defined by the configuration file
        Currenlty only support  jsonlines and text

        Returns:
          Bool: True is the changelog was properly saved, False if not
        """

        if not config.logs["change_log"]:
            return False

        if config.logs["change_log_format"] == "jsonlines":
            self.print_jsonlines()
        elif config.logs["change_log_format"] == "text":
            self.print_text()

        return True

    def print_jsonlines(self):
        """
        Write the changelog in jsonlines format in the file defined in the configuration file
        """
        jcl = {
            "timestamp": int(time() * 1000),
            "time": strftime("%Y-%m-%d %H:%M:%S"),
            "action": self.log_type,  # pylint: disable=no-member
            "object": {"id": self.obj_id, "name": self.obj_name, "type": self.obj_type,},
            "params": self.params,
        }

        with open(config.logs["change_log_filename"] + ".jsonl", "a") as file_:
            file_.write(json.dumps(jcl) + "\n")

    def print_text(self):
        """
        Write the changelog in text format in the file defined in the configuration file
        """

        log = "{time} {action} {obj_type} {obj_name} ({obj_id}) {params}".format(
            time=strftime("%Y-%m-%d %H:%M:%S"),
            action=self.log_type,  # pylint: disable=no-member
            obj_id=self.obj_id,
            obj_name=self.obj_name,
            obj_type=self.obj_type,
            params=self.params,
        )

        with open(config.logs["change_log_filename"] + ".log", "a") as file_:
            file_.write(log + "\n")


class ChangelogCreate(Changelog):
    """ """

    log_type = "create"


class ChangelogUpdate(Changelog):
    """ """

    log_type = "update"


class ChangelogDelete(Changelog):
    """ """

    log_type = "delete"
