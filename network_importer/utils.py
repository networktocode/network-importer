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


def patch_http_connection_pool(**constructor_kwargs):
    """
    This allows to override the default parameters of the
    HTTPConnectionPool constructor.
    For example, to increase the poolsize to fix problems
    with "HttpConnectionPool is full, discarding connection"
    call this function with maxsize=16 (or whatever size
    you want to give to the connection pool)

    Args:
      **constructor_kwargs: 

    Returns:

    """
    from urllib3 import connectionpool, poolmanager

    class MyHTTPConnectionPool(connectionpool.HTTPConnectionPool):
        """ """

        def __init__(self, *args, **kwargs):
            """
            

            Args:
              *args: 
              **kwargs: 

            Returns:

            """
            kwargs.update(constructor_kwargs)
            super(MyHTTPConnectionPool, self).__init__(*args, **kwargs)

    poolmanager.pool_classes_by_scheme["http"] = MyHTTPConnectionPool


def sort_by_digits(if_name):
    """
    

    Args:
      if_name: 

    Returns:

    """
    return tuple(map(int, find_digit.findall(if_name)))


def jinja_filter_toyaml_list(value):
    """
    JinjaFilter to return a dict as a Nice Yaml

    Args:
      value:  

    Returns:
      Str formatted as Yaml
    """
    return yaml.dump(value, default_flow_style=None)


def jinja_filter_toyaml_dict(value):
    """

    Args:
      value: 

    Returns:

    """
    return yaml.dump(value, default_flow_style=False)


def expand_vlans_list(vlans):
    """
    Convert string of comma separated integer (vlan) into a list

    Args:
      vlans: String (TODO add support for list)

    Returns:
      List: sorted list of vlans

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

    for v in raw_vlans_list:
        try:
            clean_vlans_list.append(int(v))
        except ValueError as e:
            logger.debug(
                f"expand_vlans_list() Unable to convert {v} as integer .. skipping"
            )

    return sorted(clean_vlans_list)
