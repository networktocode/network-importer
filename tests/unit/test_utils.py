from network_importer.utils import expand_vlans_list


def test_expand_vlans_list():

    assert expand_vlans_list("10-11") == [10, 11]
    assert expand_vlans_list("20-24") == [20, 21, 22, 23, 24]
