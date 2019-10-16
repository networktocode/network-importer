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
                generate_hostvars=dict(type="boolean", default=False),
            ),
            default={}
        ),
        batfish=dict(
            type="object", 
            properties=dict(
                address=dict(type="string", default="localhost"),
                network_name=dict(type="string"),
                snapshot_name=dict(type="string"),
            ),
            default={}
        ),
        netbox=dict(
            type="object", 
            properties=dict(
                address=dict(type="string"),
                token=dict(type="string"),
            ),
            default={}
        ),
        logs=dict(
            type="object", 
            properties=dict(
                level=dict(type="string", enum=["debug", "info", "warning"], default="info"),
                directory=dict(type="string", default=".network_importer/logs"),
                performance_log=dict(type="boolean", default=True)
            ),
            default={}
        )
    )
)
