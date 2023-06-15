"""test for the base adapter."""
from typing import List, Optional
from pydantic import BaseSettings
from network_importer.adapters.base import BaseAdapter


def test_init_no_settings_class():
    adapter = BaseAdapter(nornir="nornir_object", settings=None)
    assert adapter.nornir == "nornir_object"
    assert adapter.settings is None

    adapter = BaseAdapter(nornir="nornir_object", settings={"mysettings": "settings"})
    assert adapter.nornir == "nornir_object"
    assert adapter.settings == {"mysettings": "settings"}


def test_init_with_settings_class():
    """Validate that the settings are properly initialized with the settings_class when present."""

    class MyAdapterSettings(BaseSettings):
        """Fake adapter settings."""

        first: List[str] = list()
        second: Optional[str]

    class MyAdapter(BaseAdapter):
        """test adapter."""

        settings_class = MyAdapterSettings

        def load(self):
            """load must be defined."""

    adapter = MyAdapter(nornir="nornir_object", settings=None)
    assert adapter.nornir == "nornir_object"
    assert adapter.settings is not None
    assert adapter.settings.first == []
    assert adapter.settings.second is None

    adapter = MyAdapter(nornir="nornir_object", settings={"second": "settings"})
    assert adapter.nornir == "nornir_object"
    assert adapter.settings.first == []
    assert adapter.settings.second == "settings"
