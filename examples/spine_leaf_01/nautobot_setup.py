"""Script to add components for Nautobot."""
import os
import urllib3

import pynautobot

PLATFORMS = [
    {"name": "junos", "manufacturer": "juniper"},
    {"name": "iosxr", "manufacturer": "cisco"},
    {"name": "eos", "manufacturer": "arista"},
]

DEVICE_LIST = [
    {"name": "amarillo", "role": "spine", "type": "junos"},
    {"name": "austin", "role": "spine", "type": "iosxr"},
    {"name": "san-antonio", "role": "spine", "type": "iosxr"},
    {"name": "el-paso", "role": "spine", "type": "iosxr"},
    {"name": "dallas", "role": "leaf", "type": "iosxr"},
    {"name": "houston", "role": "leaf", "type": "eos"},
]

SITE_LIST = ["ni_spine_leaf_01"]

DEVICE_ROLES = ["spine", "leaf"]


def get_or_create(object_endpoint, search_key, search_term, **kwargs):
    created = False
    search = {search_key: search_term}
    obj = object_endpoint.get(**search)
    if obj is None:
        obj = object_endpoint.create(**search, **kwargs)
        created = True

    return obj, created


def main():
    """Main code execution block."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    nautobot = pynautobot.api(url=os.getenv("NAUTOBOT_ADDRESS"), token=os.getenv("NAUTOBOT_SUPERUSER_API_TOKEN"))
    nautobot.http_session.verify = False

    # Create region
    for region in ["ni_multi_site_02"]:
        region_obj, _ = get_or_create(
            object_endpoint=nautobot.dcim.regions, search_key="name", search_term=region, slug=region.lower()
        )

    mfg_map = dict()
    device_type_map = dict()

    for item in PLATFORMS:
        mfg, created = get_or_create(
            object_endpoint=nautobot.dcim.manufacturers,
            search_key="name",
            search_term=item["manufacturer"],
            slug=item["manufacturer"].lower(),
        )

        mfg_map[item["manufacturer"]]: mfg
        if created:
            print(f"Created manufacturer: {item['manufacturer']}")
        else:
            print(f"Manufacturer already created: {item['manufacturer']}")

        # Create device type if not already created
        device_type, created = get_or_create(
            object_endpoint=nautobot.dcim.device_types,
            search_key="model",
            search_term=item["name"],
            slug=item["name"],
            manufacturer=mfg.id,
        )

        device_type_map[item["name"]] = device_type
        if created:
            print(f"Create Device Type: {item['name']}")
        else:
            print(f"Device Type Already Created: {item['name']}")

    device_role_map = dict()

    # Create device role
    for dev_role in DEVICE_ROLES:
        device_role_obj, created = get_or_create(
            object_endpoint=nautobot.dcim.device_roles, search_key="name", search_term=dev_role, slug=dev_role,
        )

        if created:
            print(f"Created device role: {dev_role}")
        else:
            print(f"Device role already created: {dev_role}")

        device_role_map[dev_role] = device_role_obj

    # Get all of the sites
    site_map = dict()

    # Iterate over the sites
    for site in SITE_LIST:
        # Check if the device is created
        site_obj, created = get_or_create(
            object_endpoint=nautobot.dcim.sites, search_key="name", search_term=site, slug=site.lower(), status="Active"
        )

        if created:
            print(f"Created site: {site}")
        else:
            print(f"Site already created: {site}")

        site_map[site] = site_obj

    # Create Devices
    for dev in DEVICE_LIST:
        device, created = get_or_create(
            object_endpoint=nautobot.dcim.devices,
            search_key="name",
            search_term=dev["name"],
            slug=dev["name"].lower(),
            status="Active",
            site=site_map["ni_spine_leaf_01"].id,
            device_type=device_type_map[dev["type"]].id,
            device_role=device_role_map[dev["role"]].id,
        )

        if created:
            print(f"Created device: {dev['name']}")
        else:
            print(f"Device already created: {dev['name']}")


if __name__ == "__main__":
    main()
