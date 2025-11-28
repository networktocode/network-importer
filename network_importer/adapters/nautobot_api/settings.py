"""Settings definition for the NetboxAPIAdapter."""
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field

from diffsync import DiffSyncModelFlags


class AdapterSettings(BaseSettings):
    """Config settings for the netbox_api adapter. Not used currently."""

    model_flag_tags: List[str] = list()  # List of tags that defines what objects to assign the model_flag to.
    model_flag: Optional[DiffSyncModelFlags] = None  # The model flag that will be applied to objects based on tag.


class InventorySettings(BaseSettings):
    """Config settings for the NautobotAPI inventory."""

    address: Optional[str] = Field(default="http://localhost", env="NAUTOBOT_ADDRESS")
    token: Optional[str] = Field(default=None, env="NAUTOBOT_TOKEN")
    verify_ssl: Union[bool, str] = Field(default=True, env="NAUTOBOT_VERIFY_SSL")

    use_primary_ip: Optional[bool] = True
    fqdn: Optional[str] = None
    filter: Optional[str] = None
