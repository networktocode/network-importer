"""
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
import logging
import pynetbox
from dsync import DSync
# from .models import Base, NetboxSite, NetboxDevice, NetboxInterface, NetboxIPAddress, NetboxCable

from network_importer.models import * 
logger = logging.getLogger("network-importer")

source = "NetBox"

class NetBoxAdapter(DSync):

    base = Base

    # site = NetboxSite
    # device = NetboxDevice
    # interface = NetboxInterface
    # ip_address = NetboxIPAddress
    # cable = NetboxCable

    site = Site
    device = Device
    interface = Interface
    ip_address = IPAddress
    cable = Cable
    vlan = Vlan
    prefix = Prefix

    top_level = ["prefix"]

    nb = None

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.nb = None

    def init(self, url, token, filters=None):

        self.nb = pynetbox.api(
            url=url,
            token=token,
            ssl_verify=False,
        )

        session = self.start_session()

        devices_list = self.import_netbox_device(filters, session)
        # self.import_netbox_cable(devices_list, session)

        # Import Prefixes
        sites = session.query(self.site).all()
        for site in sites:
            prefixes = self.nb.ipam.prefixes.filter(site=site.name, status="container")
            
            for prefix in prefixes:
                
                prefix_type = None
                if prefix.status.value == "container":
                    prefix_type = "AGGREGATE"

                session.add(
                    self.prefix(   
                        prefix=prefix.prefix,
                        site=site,
                        prefix_type=prefix_type,
                        remote_id=prefix.id,
                    )
                )

        session.commit()

    def import_netbox_device(self, filters, session):

        nb_devs = self.nb.dcim.devices.filter(**filters)
        logger.debug(f"{source} | Found {len(nb_devs)} devices in netbox")
        device_names = []

        # -------------------------------------------------------------
        # Import Devices
        # -------------------------------------------------------------
        for device in nb_devs:

            if device.name in device_names: 
                continue

            site = session.query(self.site).filter_by(name=device.site.slug).first()
            if not site:
                session.add(self.site(name=device.site.slug, remote_id=device.site.id,))

            session.add(
                self.device(
                    name=device.name, remote_id=device.id, site_name=device.site.slug
                )
            )

            # Store all devices name in a list to speed up later verification
            device_names.append(device.name)

        # -------------------------------------------------------------
        # Import Interface & IPs
        # -------------------------------------------------------------
        # devices = session.query(self.device).all()
        # logger.debug(f"{source} | Found {len(devices)} devices in memory")

        # for dev in devices:

        #     # Import Interfaces
        #     intfs = self.nb.dcim.interfaces.filter(device=dev.name)
        #     for intf in intfs:
        #         session.add(
        #             self.interface(
        #                 name=intf.name,
        #                 device_name=dev.name,
        #                 remote_id=intf.id,
        #                 description=intf.description or None,
        #                 mtu=intf.mtu,
        #             )
        #         )

        #     # Import IP addresses
        #     ips = self.nb.ipam.ip_addresses.filter(device=dev.name)
        #     for ip in ips:
        #         session.add(
        #             self.ip_address(
        #                 address=ip.address,
        #                 device_name=dev.name,
        #                 interface_name=ip.interface.name,
        #                 remote_id=ip.id,
        #             )
        #         )

        #     logger.debug(
        #         f"{source} | Found {len(intfs)} interfaces & {len(ips)} ip addresses in netbox for {dev.name}"
        #     )

        return device_names

    def import_netbox_cable(self, device_names, session):
        sites = session.query(self.site).all()
        for site in sites:
            cables = self.nb.dcim.cables.filter(site=site.name)

            for cable in cables:
                if (
                    cable.termination_a_type != "dcim.interface"
                    or cable.termination_b_type != "dcim.interface"
                ):
                    continue

                if cable.termination_a.device.name not in device_names:
                    print(
                        f"{source} | Skipping cable {cable.id} because {cable.termination_a.device.name} is not in the list of devices"
                    )
                    continue

                elif cable.termination_b.device.name not in device_names:
                    print(
                        f"{source} | Skipping cable {cable.id} because {cable.termination_b.device.name} is not in the list of devices"
                    )
                    continue

                session.add(
                    self.cable(
                        device_a_name=cable.termination_a.device.name,
                        interface_a_name=cable.termination_a.name,
                        device_z_name=cable.termination_b.device.name,
                        interface_z_name=cable.termination_b.name,
                        remote_id=cable.id,
                    )
                )

            nbr_cables = session.query(self.cable).count()
            logger.debug(
                f"{source} | Found {nbr_cables} cables in netbox for {site.name}"
            )


    # -----------------------------------------------------
    # Interface
    # -----------------------------------------------------
    def create_interface(self, keys, params, session=None):

        nb_params = {}
        nb_params.update(keys)
        nb_params.update(params)

        # import pdb;pdb.set_trace()
        device = session.query(self.device).filter_by(name=keys["device_name"]).first()
        nb_params["device"] = device.remote_id
        del nb_params["device_name"]

        if "description" in nb_params and not nb_params["description"]:
            nb_params["description"] = ""

        nb_params["type"] = "other"

        intf = self.nb.dcim.interfaces.create(**nb_params)
        logger.info(f"Created interface {intf.name} ({intf.id}) in NetBox")

        # Create the object in the local DB
        item = self.default_create(
            object_type="interface", keys=keys, params=params, session=session
        )
        item.remote_id = intf.id

        return item

    def update_interface(self, keys, params, session=None):

        item = session.query(self.interface).filter_by(**keys).first()

        attrs = item.get_attrs()
        if attrs == params:
            return item

        if "description" in params and not params["description"]:
            params["description"] = ""

        intf = self.nb.dcim.interfaces.get(item.remote_id)
        intf.update(data=params)

        for key, value in params.items():
            setattr(item, key, value)

        return item

    def delete_interface(self, keys, params, session=None):

        item = session.query(self.interface).filter_by(**keys).first()

        intf = self.nb.dcim.interfaces.get(item.remote_id)
        intf.delete()

        item = self.default_delete(
            object_type="interface", keys=keys, params=params, session=session
        )
        
        return item

    # -----------------------------------------------------
    # Cable
    # -----------------------------------------------------
    def create_cable(self, keys, params, session=None):

        interface_a = (
            session.query(self.interface)
            .filter_by(
                name=keys["interface_a_name"], device_name=keys["device_a_name"],
            )
            .first()
        )
        interface_z = (
            session.query(self.interface)
            .filter_by(
                name=keys["interface_z_name"], device_name=keys["device_z_name"],
            )
            .first()
        )

        cable = self.nb.dcim.cables.create(
            termination_a_type="dcim.interface",
            termination_b_type="dcim.interface",
            termination_a_id=interface_a.remote_id,
            termination_b_id=interface_z.remote_id,
        )

        # Create the object in the local DB
        item = self.default_create(
            object_type="cable", keys=keys, params=params, session=session
        )
        item.remote_id = cable.id

        return item

    def delete_cable(self, keys, params, session=None):
        pass

    # -----------------------------------------------------
    # IP Address
    # -----------------------------------------------------
    def create_ip_address(self, keys, params, session=None):

        interface = None
        if "interface_name" in params and "device_name" in params:
            interface = session.query(self.interface).filter_by(
                    name=params["interface_name"], device_name=params["device_name"],
                ).first()

        if interface:
            ip_address = self.nb.ipam.ip_addresses.create(
                address=keys["address"],
                interface=interface.remote_id
            )
        else:
            ip_address = self.nb.ipam.ip_addresses.create(
                address=keys["address"]
            )

        item = self.default_create(
            object_type="ip_address", keys=keys, params=params, session=session
        )
        item.remote_id = ip_address.id

        return item

    def delete_ip_address(self, keys, params, session=None):

        item = session.query(self.ip_address).filter_by(**keys).first()

        ip = self.nb.ipam.ip_addresses.get(item.remote_id)
        ip.delete()

        item = self.default_delete(
            object_type="ip_address", keys=keys, params=params, session=session
        )

        return item

    # -----------------------------------------------------
    # Prefix
    # -----------------------------------------------------
    def create_prefix(self, keys, params, session=None):
        
        site = session.query(self.site).filter_by(name=keys["site_name"]).first()

        status = "active"
        if params["prefix_type"] == "AGGREGATE":
            status = "container"

        prefix = self.nb.ipam.prefixes.create(
                prefix=keys["prefix"],
                site=site.remote_id,
                status=status
            )

        item = self.default_create(
            object_type="prefix", keys=keys, params=params, session=session
        )
        item.remote_id = prefix.id

    # def update_prefix(self, keys, params, session=None):
    #     pass

    # def delete_prefix(self, keys, params, session=None):
    #     pass

    # -----------------------------------------------------
    # Vlans
    # -----------------------------------------------------
    # def create_vlan(self, keys, params, session=None):
    #     pass
    
    # def delete_vlan(self, keys, params, session=None):
    #     pass