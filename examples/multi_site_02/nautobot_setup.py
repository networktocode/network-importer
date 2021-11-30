"""Script to add components for Nautobot."""
import os
import urllib3

import pynautobot

# pylint: disable=too-many-locals
# pylint: disable=too-many-branches

PLATFORMS = [
    {"name": "junos", "manufacturer": "juniper"},
    {"name": "iosxr", "manufacturer": "cisco"},
    {"name": "ios", "manufacturer": "cisco"},
    {"name": "nxos", "manufacturer": "cisco"},
    {"name": "eos", "manufacturer": "arista"},
]

DEVICE_LIST = [
    {"name": "nyc-bb-01", "role": "router", "type": "ios"},
    {"name": "nyc-rtr-01", "role": "router", "type": "ios"},
    {"name": "nyc-rtr-02", "role": "router", "type": "ios"},
    {"name": "nyc-spine-01", "role": "spine", "type": "nxos"},
    {"name": "nyc-spine-02", "role": "spine", "type": "nxos"},
    {"name": "nyc-leaf-01", "role": "leaf", "type": "nxos"},
    {"name": "hou-bb-01", "role": "router", "type": "ios"},
    {"name": "hou-rtr-01", "role": "router", "type": "junos"},
    {"name": "hou-rtr-02", "role": "router", "type": "junos"},
    {"name": "hou-spine-01", "role": "spine", "type": "eos"},
    {"name": "hou-spine-02", "role": "spine", "type": "eos"},
    {"name": "hou-leaf-01", "role": "leaf", "type": "eos"},
    {"name": "hou-leaf-02", "role": "leaf", "type": "eos"},
    {"name": "sjc-bb-01", "role": "router", "type": "ios"},
    {"name": "sjc-rtr-01", "role": "router", "type": "iosxr"},
    {"name": "sjc-rtr-02", "role": "router", "type": "iosxr"},
    {"name": "sjc-leaf-01", "role": "leaf", "type": "eos"},
]

SITE_LIST = ["hou", "nyc", "sjc"]

DEVICE_ROLES = ["spine", "leaf", "router"]


def get_or_create(object_endpoint, search_key, search_term, **kwargs):
    """Get or create object with pynautobot.

    Args:
        object_endpoint (pynautobot Endpoint): Endpoint to make get and post requests to
        search_key (str): Key to use within the get request, such as name or model
        search_term (str): What is being searched for

    Returns:
        obj (pynautobot object), created (bool): Object being created, and whether or not it was created
    """
    created = False
    search = {search_key: search_term}
    if kwargs.get("just_create_device"):
        try:
            print("Just creating device")
            obj = object_endpoint.create(**search, **kwargs)
            created = True
            return obj, created
        except:  # pylint: disable=bare-except # noqa: E722, E261
            return None, True

    obj = object_endpoint.get(**search)
    if obj is None:
        obj = object_endpoint.create(**search, **kwargs)
        created = True

    return obj, created


def main():
    """Main code execution block."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    nautobot = pynautobot.api(url=os.getenv("NAUTOBOT_ADDRESS"), token=os.getenv("NAUTOBOT_TOKEN"))
    nautobot.http_session.verify = False

    # Create region
    for region in ["ni_multi_site_02"]:
        print(f"Checking on region: {region}")
        _, created = get_or_create(
            object_endpoint=nautobot.dcim.regions, search_key="name", search_term=region, slug=region.lower()
        )

        if created:
            print(f"Created region: {region}")
        else:
            print(f"Region already exists: {region}")

    mfg_map = dict()
    device_type_map = dict()

    for item in PLATFORMS:
        print(f"Checking on platform: {item}")
        mfg, created = get_or_create(
            object_endpoint=nautobot.dcim.manufacturers,
            search_key="slug",
            search_term=item["manufacturer"],
            name=item["manufacturer"].capitalize(),
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
        print(f"Checking on device role: {dev_role}")
        device_role_obj, created = get_or_create(
            object_endpoint=nautobot.dcim.device_roles,
            search_key="name",
            search_term=dev_role,
            slug=dev_role,
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
        print(f"Checking on site: {site}")
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
        print(f"Creating device: {dev}")
        _, created = get_or_create(
            object_endpoint=nautobot.dcim.devices,
            search_key="name",
            search_term=dev["name"],
            slug=dev["name"].lower(),
            status="Active",
            site=site_map["ni_spine_leaf_01"].id,
            device_type=device_type_map[dev["type"]].id,
            device_role=device_role_map[dev["role"]].id,
            just_create_device=True,
        )

        if created:
            print(f"Created device: {dev['name']}")
        else:
            print(f"Device already created: {dev['name']}")


if __name__ == "__main__":
    main()
