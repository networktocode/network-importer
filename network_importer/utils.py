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

import time
import re
import logging

find_digit = re.compile(r"\D?(\d+)\D?")

logger = logging.getLogger("network-importer")


def sort_by_digits(if_name):
    return tuple(map(int, find_digit.findall(if_name)))


def jinja_filter_toyaml_list(value):
    return yaml.dump(value, default_flow_style=None)


def jinja_filter_toyaml_dict(value):
    return yaml.dump(value, default_flow_style=False)


def expand_vlans_list(vlans):
    """
    Input:
        String (TODO add support for list)

    Return List
    """
    raw_vlans_list = []
    clean_vlans_list = []

    vlans_csv = str(vlans).split(",")

    for vlan in vlans_csv:
        min_max = str(vlan).split("-")
        if len(min_max) == 1:
            raw_vlans_list.append(vlan)
        elif len(min_max) == 2:
            raw_vlans_list.extend(range(int(min_max[0]), int(min_max[1]) + 1))

        # Pass if min_max biggest than 2

    for v in raw_vlans_list:
        try:
            clean_vlans_list.append(int(v))
        except ValueError as e:
            logger.debug(
                f"expand_vlans_list() Unable to convert {v} as integer .. skipping"
            )

    return sorted(clean_vlans_list)
