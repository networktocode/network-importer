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

import toml
import os.path
from pathlib import Path

"""
Jsonschema definition for the configuation file (network_importer.toml by default)
"""
config_schema = dict(
    type="object",
    properties=dict(
        main=dict(
            type="object",
            properties=dict(
                import_ips=dict(type="boolean", default=True),
                import_cabling=dict(type="boolean", default=True),
                import_vlans=dict(
                    type="string", enum=["cli", "config", "no"], default="config"
                ),
                generate_hostvars=dict(type="boolean", default=False),
                hostvars_directory=dict(type="string", default="host_vars"),
                nbr_workers=dict(type="integer", default=10),
                inventory_source=dict(
                    type="string", enum=["netbox", "configs"], default="netbox"
                ),
                inventory_filter=dict(type="string"),
                configs_directory=dict(type="string", default="configs"),
            ),
            default={},
        ),
        batfish=dict(
            type="object",
            properties=dict(
                address=dict(type="string", default="localhost"),
                network_name=dict(type="string"),
                snapshot_name=dict(type="string"),
            ),
            default={},
        ),
        netbox=dict(
            type="object",
            properties=dict(address=dict(type="string"), token=dict(type="string")),
            default={},
        ),
        network=dict(
            type="object",
            properties=dict(login=dict(type="string"), password=dict(type="string")),
            default={},
        ),
        logs=dict(
            type="object",
            properties=dict(
                level=dict(
                    type="string", enum=["debug", "info", "warning"], default="info"
                ),
                directory=dict(type="string", default=".network_importer/logs"),
                performance_log=dict(type="boolean", default=True),
            ),
            default={},
        ),
    ),
)
