"""Test utilities."""

from network_importer.utils import (
    expand_vlans_list,
    sort_by_digits,
    is_interface_physical,
    is_interface_lag,
    is_mac_address,
    build_filter_params,
)


def test_expand_vlans_list():
    """
    Test expand VLANs
    """

    assert expand_vlans_list("10-11") == [10, 11]
    assert expand_vlans_list("20-24") == [20, 21, 22, 23, 24]


def test_sort_by_digits():
    """
    Test sort by digits
    """

    assert sort_by_digits("Eth0/2/3") == (
        0,
        2,
        3,
    )
    assert sort_by_digits("Eth0/2/543/14/6") == (
        0,
        2,
        543,
        14,
        6,
    )
    assert sort_by_digits("Eth0") == (0,)
    assert not sort_by_digits("Eth")


def test_is_interface_physical():
    # pylint: disable=C0121
    """
    Test is_interface_physical
    """
    assert is_interface_physical("GigabitEthernet0/0/2") is True
    assert is_interface_physical("GigabitEthernet0/0/2.890") is False
    assert is_interface_physical("GigabitEthernet0/0/2.1") is False
    assert is_interface_physical("Ethernet0.1") is False
    assert is_interface_physical("Ethernet1") is True
    assert is_interface_physical("Serial0/1/0:15") is True
    assert is_interface_physical("Service-Engine0/1/0") is True
    assert is_interface_physical("Service-Engine0/1/0.152") is False
    assert is_interface_physical("GigabitEthernet0") is True
    assert is_interface_physical("ge-0/0/0") is True
    assert is_interface_physical("ge-0/0/0.10") is False
    assert is_interface_physical("lo0.0") is False
    assert is_interface_physical("Loopback1") is False
    assert is_interface_physical("Vlan108") is False
    assert is_interface_physical("ae0.100") is False
    assert is_interface_physical("Management0/0") is True


def test_is_interface_lag():
    # pylint: disable=C0121
    """
    Test is_interface_log
    """
    assert is_interface_lag("port-channel100") is True
    assert is_interface_lag("Port-Channel100") is True
    assert is_interface_lag("ae0") is True
    assert is_interface_lag("ae0.100") is None
    assert is_interface_lag("Port-Channel100") is True
    assert is_interface_lag("Port-Channel100.100") is None
    assert is_interface_lag("GigabitEthernet0/0/2") is None
    assert is_interface_lag("GigabitEthernet0/0/2.890") is None
    assert is_interface_lag("GigabitEthernet0/0/2.1") is None
    assert is_interface_lag("Ethernet0.1") is None
    assert is_interface_lag("Ethernet1") is None
    assert is_interface_lag("Serial0/1/0:15") is None
    assert is_interface_lag("Service-Engine0/1/0") is None
    assert is_interface_lag("Service-Engine0/1/0.152") is None
    assert is_interface_lag("GigabitEthernet0") is None
    assert is_interface_lag("ge-0/0/0") is None
    assert is_interface_lag("ge-0/0/0.10") is None
    assert is_interface_lag("lo0.0") is None
    assert is_interface_lag("Loopback1") is None
    assert is_interface_lag("Vlan108") is None
    assert is_interface_lag("Management0/0") is None


def test_is_mac_address():
    # pylint: disable=C0121
    assert is_mac_address("f8:f2:1e:89:3c:61") is True
    assert is_mac_address("F8f2.1e89.3c61") is True
    assert is_mac_address("F8f2.1e89.3c") is False
    assert is_mac_address("F8f2.1e89.3c66.67") is False
    assert is_mac_address("not a mac address") is False


def test_build_filter_params():
    # base implementation
    params = {}
    build_filter_params(["site=nyc", "device=dev"], params)
    assert params == {"device": "dev", "site": "nyc"}

    params = {}
    build_filter_params(["device=dev"], params)
    assert params == {"device": "dev"}

    # multiple filter of the same type
    params = {}
    build_filter_params(["site=nyc", "site=jcy"], params)
    assert params == {"site": ["nyc", "jcy"]}

    params = {}
    build_filter_params(["device=dev"], params)
    assert params == {"device": "dev"}

    # Existing keys in params should be preserved
    params = {"site": "jcy"}
    build_filter_params(["site=nyc", "device=dev"], params)
    assert params == {"device": "dev", "site": ["jcy", "nyc"]}

    # Invalid string (no =) will be ignored
    params = {"site": "jcy"}
    build_filter_params(["site", "device=dev"], params)
    assert params == {"device": "dev", "site": "jcy"}
