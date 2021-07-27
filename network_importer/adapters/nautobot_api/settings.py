"""Settings definition for the NetboxAPIAdapter."""
from typing import List, Optional, Union
from pydantic import BaseSettings

from diffsync import DiffSyncModelFlags


class AdapterSettings(BaseSettings):
    """Config settings for the netbox_api adapter. Not used currently."""

    model_flag_tags: List[str] = list()  # List of tags that defines what objects to assign the model_flag to.
    model_flag: Optional[DiffSyncModelFlags]  # The model flag that will be applied to objects based on tag.


class InventorySettings(BaseSettings):
    """Config settings for the NautobotAPI inventory."""

    address: Optional[str] = "http://localhost"
    token: Optional[str] = None
    verify_ssl: Union[bool, str] = True

    use_primary_ip: Optional[bool] = True
    fqdn: Optional[str] = None
    filter: Optional[str] = None

    class Config:
        """Additional parameters to automatically map environment variable to some settings."""

        fields = {
            "address": {"env": "NAUTOBOT_ADDRESS"},
            "token": {"env": "NAUTOBOT_TOKEN"},
            "verify_ssl": {"env": "NAUTOBOT_VERIFY_SSL"},
        }
