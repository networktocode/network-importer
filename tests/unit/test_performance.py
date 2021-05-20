"""unit tests for network_importer.performance."""

from network_importer.performance import print_from_ms


def test_print_from_ms():
    """
    Verify output of print from ms
    """

    assert print_from_ms(10) == "10ms"
    assert print_from_ms(1010) == "1s 10ms"
    assert print_from_ms(60010) == "1m 0s 10ms"
    assert print_from_ms(61010) == "1m 1s 10ms"
