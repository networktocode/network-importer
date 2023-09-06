"""unit test for config related functions."""
import pytest

from network_importer.exceptions import ConfigLoadFatalError
from network_importer.config import _configure_backend, Settings, DEFAULT_BACKENDS

TEST_BACKEND = list(DEFAULT_BACKENDS.keys())[0]


def test_configure_backend_w_backend():
    result = _configure_backend(Settings(main=dict(backend=TEST_BACKEND)))
    assert result.inventory.inventory_class is not None
    assert result.adapters.sot_class is not None

    result = _configure_backend(
        Settings(main=dict(backend=TEST_BACKEND), inventory=dict(inventory_class="myinventoryclass"))
    )
    assert result.inventory.inventory_class == "myinventoryclass"
    assert result.adapters.sot_class is not None

    result = _configure_backend(Settings(main=dict(backend=TEST_BACKEND), adapters=dict(sot_class="mysotclass")))
    assert result.inventory.inventory_class is not None
    assert result.adapters.sot_class == "mysotclass"


def test_configure_backend_wo_backend():
    with pytest.raises(ConfigLoadFatalError):
        _configure_backend(Settings())

    with pytest.raises(ConfigLoadFatalError):
        _configure_backend(Settings(inventory=dict(inventory_class="myinventoryclass")))

    result = _configure_backend(
        Settings(adapters=dict(sot_class="mysotclass"), inventory=dict(inventory_class="myinventoryclass"))
    )
    assert result.adapters.sot_class == "mysotclass"
    assert result.inventory.inventory_class == "myinventoryclass"
