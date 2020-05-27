

import logging
import pynetbox
from netmod import NetMod
from .models import *

logger = logging.getLogger("network-importer")

source = "NetBox"

class NetModNetBox(NetMod):

    site = NetboxSite
    device = NetboxDevice
    interface = NetboxInterface
    ip_address = NetboxIPAddress
    cable = NetboxCable

    def __init__(self, *args, **kwargs):
        super(NetModNetBox, self).__init__(*args, **kwargs)
        self.nb = None

    def init(self):

        device_names = []

        self.nb = pynetbox.api(
            url="http://localhost",
            token="1234567890abcdefghijklmnopqrstuvwxyz0123",
            ssl_verify=False,
        )

        session = self.start_session()

        nb_devs = self.nb.dcim.devices.filter(site="ni_example_01")
        logger.debug(f"{source} | Found {len(nb_devs)} devices in netbox")

        # -------------------------------------------------------------
        # Import Devices
        # -------------------------------------------------------------
        for device in nb_devs:

            site = session.query(self.site).filter_by(name=device.site.slug).first()
            if not site:
                session.add(
                    self.site(
                        name=device.site.slug, 
                        remote_id=device.site.id,
                    )
                )

            session.add(
                self.device(
                    name=device.name, 
                    remote_id=device.id,
                    site_name=device.site.slug
                )
            )

            # Store all devices name in a list to speed up later verification
            device_names.append(device.name)

        # -------------------------------------------------------------
        # Import Interface & IPs
        # -------------------------------------------------------------
        devices = session.query(self.device).all()
        logger.debug(f"{source} | Found {len(devices)} devices in memory")

        for dev in devices:

            # Import Interfaces
            intfs = self.nb.dcim.interfaces.filter(device=dev.name)
            for intf in intfs:
                session.add(
                    self.interface(
                        name=intf.name,
                        device_name=dev.name,
                        remote_id=intf.id,
                        description=intf.description or None,
                        mtu=intf.mtu
                    )
                )

            # Import IP addresses
            ips = self.nb.ipam.ip_addresses.filter(device=dev.name)
            for ip in ips:
                session.add(
                    self.ip_address(
                        address=ip.address,
                        device_name=dev.name,
                        remote_id=ip.interface.name
                    )
                )

            logger.debug(f"{source} | Found {len(intfs)} interfaces & {len(ips)} ip addresses in netbox for {dev.name}")

        # -------------------------------------------------------------
        # Import Cables
        # -------------------------------------------------------------
        sites = session.query(self.site).all()
        for site in sites:
            cables = self.nb.dcim.cables.filter(site=site.name)

            for cable in cables:
                if cable.termination_a_type != "dcim.interface" or cable.termination_b_type != "dcim.interface":
                    continue

                if cable.termination_a.device.name not in device_names:
                    print(f"{source} | Skipping cable {cable.id} because {cable.termination_a.device.name} is not in the list of devices")
                    continue

                elif cable.termination_b.device.name not in device_names:
                    print(f"{source} | Skipping cable {cable.id} because {cable.termination_b.device.name} is not in the list of devices")
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

            nbr_cables = session.query(self.cable.id).count()
            logger.debug(f"{source} | Found {nbr_cables} cables in netbox for {site.name}")

        session.commit()

    def create_interface(self, keys, params, session=None):

        nb_params = {}
        nb_params.update(keys)
        nb_params.update(params)
        
        # import pdb;pdb.set_trace()
        device = session.query(self.device).filter(self.device.name == item.device_name).first()
        nb_params["device"] = device.remote_id
        del nb_params["device_name"]

        if "description" in nb_params and not nb_params["description"]:
            nb_params["description"] = ""

        nb_params["type"] = "other"

        intf = self.nb.dcim.interfaces.create(
            **nb_params
        )
        logger.info(f"Created interface {intf.name} ({intf.id}) in NetBox")
        
        # Create the object in the local DB
        item = self.default_create(
                object_type="interface",
                keys=keys,
                params=params,
                session=session
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

        # item = self.default_update(
        #         object_type="interface",
        #         keys=keys,
        #         params=params,
        #         session=session
        #     )

    #     # import pdb;pdb.set_trace()
    #     device = session.query(self.device).filter(self.device.name == item.device_name).first()
    #     keys["device"] = device.remote_id
    #     del keys["device_name"]

    #     if "description" in params and not params["description"]:
    #         params["description"] = ""

    #     params["type"] = "other"

    #     intf = self.nb.dcim.interfaces.create(
    #         **keys, **params
    #     )
    #     logger.info(f"Created interface {intf.name} ({intf.id}) in NetBox")
    #     item.remote_id = intf.id

    #     return item
        