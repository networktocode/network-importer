import re
import logging
import glob
import yaml
import os
from netmod import NetMod

logger = logging.getLogger("network-importer")


class NetModYaml(NetMod):

    top_level = ["device"]

    def init(self, directory="."):

        session = self.start_session()

        sites_list = os.listdir(f"{directory}/sites/")

        for site_name in sites_list:
            site = session.query(self.site).filter_by(name=site_name).first()
            if not site:
                session.add(self.site(name=site_name))

            logger.debug(f"Add site {site_name}")

            device_list = mylist = [
                f for f in glob.glob(f"{directory}/sites/{site_name}/devices/*.yaml")
            ]

            for device_file in device_list:

                device_name = device_file.split("/").pop().replace(".yaml", "")
                session.add(self.device(name=device_name, site_name=site_name))
                logger.debug(f"Add Device {device_name}")

                data = yaml.safe_load(open(device_file))
                if "interfaces" not in data:
                    continue

                for intf_name, intf_data in data["interfaces"].items():
                    values = {}
                    intf = self.interface(name=intf_name, device_name=device_name)
                    for attr in self.interface.attributes:
                        if attr in intf_data:
                            setattr(intf, attr, intf_data[attr])

                    session.add(intf)

                    if "ips" in intf_data and isinstance(intf_data["ips"], dict):
                        for ip, ip_data in intf_data["ips"].items():

                            session.add(
                                self.ip_address(
                                    address=ip,
                                    interface_name=intf_name,
                                    device_name=device_name,
                                )
                            )

        session.commit()
