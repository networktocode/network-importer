"""
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
import pytest
from diffsync.exceptions import ObjectNotFound

import network_importer.config as config
from network_importer.models import Interface, IPAddress, Prefix


def test_load_batfish_ipaddress_w_ip_w_prefix_no_vlan(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)
    intf1 = Interface(name="et-0/0/0", device_name=dev_spine1.name)

    config.load(config_data=dict(main=dict(backend="nautobot", import_ips=True, import_prefixes=True)))

    ipaddr = adapter.load_batfish_ip_address(site=site_sfo, device=dev_spine1, interface=intf1, address="10.10.10.1/24")
    prefix = Prefix(prefix="10.10.10.0/24", site_name="sfo")

    assert isinstance(ipaddr, IPAddress)
    assert adapter.get(IPAddress, identifier=ipaddr.get_unique_id())
    assert adapter.get(Prefix, identifier=prefix.get_unique_id())


def test_load_batfish_ipaddress_wo_ip_wo_prefix(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)
    intf1 = Interface(name="et-0/0/0", device_name=dev_spine1.name)

    config.load(config_data=dict(main=dict(backend="nautobot", import_ips=False, import_prefixes=False)))

    ipaddr = adapter.load_batfish_ip_address(site=site_sfo, device=dev_spine1, interface=intf1, address="10.10.10.1/24")
    prefix = Prefix(prefix="10.10.10.0/24", site_name="sfo")

    assert isinstance(ipaddr, IPAddress)
    with pytest.raises(ObjectNotFound):
        assert adapter.get(IPAddress, identifier=ipaddr.get_unique_id()) is None
    with pytest.raises(ObjectNotFound):
        assert adapter.get(Prefix, identifier=prefix.get_unique_id()) is None


def test_load_batfish_ipaddress_w_ip_wo_prefix(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)
    intf1 = Interface(name="et-0/0/0", device_name=dev_spine1.name)

    config.load(config_data=dict(main=dict(backend="nautobot", import_ips=True, import_prefixes=False)))

    ipaddr = adapter.load_batfish_ip_address(site=site_sfo, device=dev_spine1, interface=intf1, address="10.10.10.1/24")
    prefix = Prefix(prefix="10.10.10.0/24", site_name="sfo")

    assert isinstance(ipaddr, IPAddress)
    assert adapter.get(IPAddress, identifier=ipaddr.get_unique_id())
    with pytest.raises(ObjectNotFound):
        assert adapter.get(Prefix, identifier=prefix.get_unique_id()) is None


def test_load_batfish_ipaddress_wo_ip_w_prefix(network_importer_base, site_sfo, dev_spine1):

    adapter = network_importer_base
    adapter.add(site_sfo)
    adapter.add(dev_spine1)
    intf1 = Interface(name="et-0/0/0", device_name=dev_spine1.name)

    config.load(config_data=dict(main=dict(backend="nautobot", import_ips=False, import_prefixes=True)))

    ipaddr = adapter.load_batfish_ip_address(site=site_sfo, device=dev_spine1, interface=intf1, address="10.10.10.1/24")
    prefix = Prefix(prefix="10.10.10.0/24", site_name="sfo")

    assert isinstance(ipaddr, IPAddress)
    with pytest.raises(ObjectNotFound):
        assert adapter.get(IPAddress, identifier=ipaddr.get_unique_id()) is None
    assert adapter.get(Prefix, identifier=prefix.get_unique_id())
