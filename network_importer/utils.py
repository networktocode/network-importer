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

import re
import logging
from urllib3 import connectionpool, poolmanager
import yaml

logger = logging.getLogger("network-importer")  # pylint: disable=C0103


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


def sort_by_digits(if_name: str) -> tuple:
    """
    Extract all digits from a string and return them as tuple

    Args:
      if_name:

    Returns:
      tuple of all digits in the string

    """
    find_digit = re.compile(r"\D?(\d+)\D?")
    return tuple(map(int, find_digit.findall(if_name)))


def is_interface_physical(name):  # pylint: disable=R0911
    """
    Function evaluate if an interface is likely to be a physical interface

    Args:
      name: str name of the interface to evaluate

    Return:
      True, False or None
    """

    # Match most physical interface Cisco that contains Ethernet
    #  GigabitEthernet0/0/2
    #  GigabitEthernet0/0/2:3
    #  TenGigabitEthernet0/0/4
    cisco_physical_intf = r"^[a-zA-Z]+[Ethernet][0-9\/\:]+$"

    # Match Sub interfaces finishing with ".<number>"
    sub_intf = r".*\.[0-9]+$"

    # Regex for loopback and vlan interface
    loopback = r"^(L|l)(oopback|o)[0-9]+$"
    vlan = r"^(V|v)(lan)[0-9]+$"

    # Generic physical interface match
    #  mainly looking for <int>/<int> or <int>/<int>/<int> at the end
    generic_physical_intf = r"^[a-zA-Z\-]+[0-9]+\/[0-9\/\:]+$"

    # Match Juniper Interfaces
    jnpr_physical_intf = r"^[a-z]+\-[0-9\/\:]+$"

    if re.match(loopback, name):
        return False
    if re.match(vlan, name):
        return False
    if re.match(cisco_physical_intf, name):
        return True
    if re.match(sub_intf, name):
        return False
    if re.match(jnpr_physical_intf, name):
        return True
    if re.match(generic_physical_intf, name):
        return True

    return None


def is_interface_lag(name):
    """
    Function evaluate if an interface is likely to be a lag

    Args:
      name: str name of the interface to evaluate
      vendor: str name of the vendor (optional)

    Return:
      True, False or None
    """

    port_channel_intf = r"^port\-channel[0-9]+$"
    po_intf = r"^po[0-9]+$"
    ae_intf = r"^ae[0-9]+$"

    if re.match(port_channel_intf, name.lower()):
        return True
    if re.match(ae_intf, name):
        return True
    if re.match(po_intf, name):
        return True

    return None


def jinja_filter_toyaml_list(value) -> str:
    """
    JinjaFilter to return a dict as a Nice Yaml

    Args:
      value:

    Returns:
      Str formatted as Yaml
    """
    return yaml.dump(value, default_flow_style=None)


def jinja_filter_toyaml_dict(value) -> str:
    """

    Args:
      value:

    Returns:

    """
    return yaml.dump(value, default_flow_style=False)


def expand_vlans_list(vlans: str) -> list:
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

    for vlan_ in raw_vlans_list:
        try:
            clean_vlans_list.append(int(vlan_))
        except ValueError as exc:
            logger.debug(
                f"expand_vlans_list() Unable to convert {vlan_} as integer .. skipping"
            )

    return sorted(clean_vlans_list)


def build_filter_params(filter_params, params):
    """
    Update parms dict() with filter args in required format
    for pynetbox
    Args:
      filter_parmas: split string from cli or config
      parms: dict() object to hold params
    Returns:
    """
    for param_value in filter_params:
        if "=" not in param_value:
            continue
        key, value = param_value.split("=", 1)
        existing_value = params.get(key)
        if existing_value and isinstance(existing_value, list):
            params[key].append(value)
        elif existing_value and isinstance(existing_value, str):
            params[key] = [existing_value, value]
        else:
            params[key] = value
