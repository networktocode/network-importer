from network_importer.remote import netbox
import network_importer.config as config

DRIVERS = {
    "netbox": {
        "default": {
            "interface": netbox.Netbox26Interface,
            "vlan": netbox.NetboxVlan,
            "ip_address": netbox.NetboxIPAddress,
            "optic": netbox.NetboxOptic,
        },
        "2.7": {"interface": netbox.Netbox27Interface},
    }
}


def get_driver(dtype):

    backend = config.main["backend_type"]
    version = config.main["backend_version"]

    if (
        version != "default"
        and version in DRIVERS[backend].keys()
        and dtype in DRIVERS[backend][version].keys()
    ):
        return DRIVERS[backend][version][dtype]

    return DRIVERS[backend]["default"][dtype]
