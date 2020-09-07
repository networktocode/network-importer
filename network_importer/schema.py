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
# pylint: disable=invalid-name
# Jsonschema definition for the configuation file (network_importer.toml by default)

config_schema = dict(
    type="object",
    properties=dict(
        main=dict(
            type="object",
            properties=dict(
                import_ips=dict(type="boolean", default=True),
                import_prefixes=dict(type="boolean", default=False),
                import_cabling=dict(type=["string", "boolean"], enum=["lldp", "cdp", "config", False], default="lldp",),
                import_transceivers=dict(type="boolean", default=False),
                import_intf_status=dict(type="boolean", default=True),
                import_vlans=dict(type=["string", "boolean"], enum=["cli", "config", True, False], default="config",),
                generate_hostvars=dict(type="boolean", default=False),
                hostvars_directory=dict(type="string", default="host_vars"),
                nbr_workers=dict(type="integer", default=25),
                inventory_source=dict(type="string", enum=["netbox", "configs"], default="netbox"),
                inventory_filter=dict(type="string"),
                configs_directory=dict(type="string", default="configs"),
                data_directory=dict(type="string", default="data"),
                data_update_cache=dict(type="boolean", default=True),
                data_use_cache=dict(type="boolean", default=False),
                backend_type=dict(type="string", enum=["netbox"], default="netbox"),
                backend_version=dict(type="string", default="default"),
                excluded_platforms_cabling=dict(type="array", items=dict(type="string"), default=[]),
            ),
            default={},
        ),
        batfish=dict(
            type="object",
            properties=dict(
                address=dict(type="string", default="localhost"),
                network_name=dict(type="string", default="network-importer"),
                snapshot_name=dict(type="string", default="latest"),
                port_v1=dict(type="number", min=0, default=9997),
                port_v2=dict(type="number", min=0, default=9996),
                use_ssl=dict(type="boolean", default=False),
                api_key=dict(type=["string", "null"], default=None),
            ),
            default={},
        ),
        netbox=dict(
            type="object",
            properties=dict(
                address=dict(type="string", default="http://localhost"),
                token=dict(type=["string", "null"]),
                supported_platforms=dict(type="array", items=dict(type="string"), default=[]),
                status_update=dict(type="boolean", default=False),
                status_on_pass=dict(type="number", min=0, default=1),
                status_on_fail=dict(type="number", min=0, default=4),
                status_on_unreachable=dict(type="number", min=0, default=0),
                cacert=dict(type=["string", "null"]),
                verify_ssl=dict(type="boolean", default=True),
            ),
            default={},
        ),
        network=dict(
            type="object",
            properties=dict(
                login=dict(type=["string", "null"], default=None),
                password=dict(type=["string", "null"], default=None),
                enable=dict(type="boolean", default=True),
            ),
            default={},
        ),
        logs=dict(
            type="object",
            properties=dict(
                level=dict(type="string", enum=["debug", "info", "warning"], default="info"),
                directory=dict(type="string", default="logs"),
                performance_log=dict(type="boolean", default=True),
                performance_log_directory=dict(type="string", default="performance_logs"),
                change_log=dict(type="boolean", default=True),
                change_log_format=dict(type="string", enum=["jsonlines", "text"], default="text"),
                change_log_filename=dict(type="string", default="changelog"),
            ),
            default={},
        ),
    ),
)
