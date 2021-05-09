"""Settings definition for the NetboxAPIAdapter.

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
from typing import List, Optional, Union
from pydantic import BaseSettings

from diffsync import DiffSyncModelFlags

# pylint: disable=too-few-public-methods,no-self-argument,no-self-use

class AdapterSettings(BaseSettings):
    """Config settings for the netbox_api adapter. Not used currently."""

    model_flag_tags: List[str] = list()  # List of tags that defines what objects to assign the model_flag to.
    model_flag: Optional[DiffSyncModelFlags]  # The model flag that will be applied to objects based on tag.


class InventorySettings(BaseSettings):
    address: Optional[str] = "http://localhost"
    token: Optional[str] = None
    verify_ssl: Union[bool, str] = True

    use_primary_ip: Optional[bool] = True
    fqdn: Optional[str] = None
    filter: Optional[str] = None
    global_delay_factor: Optional[int] = 5
    banner_timeout: Optional[int] = 15
    conn_timeout: Optional[int] = 5

    class Config:
        """Additional parameters to automatically map environment variable to some settings."""

        fields = {
            "address": {"env": "NAUTOBOT_ADDRESS"},
            "token": {"env": "NAUTOBOT_TOKEN"},
            "verify_ssl": {"env": "NAUTOBOT_VERIFY_SSL"},
        }
