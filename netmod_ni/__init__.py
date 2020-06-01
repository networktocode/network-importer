import re
import logging
from pybatfish.client.session import Session
from netmod import NetMod

logger = logging.getLogger("network-importer")


class NetModNi(NetMod):

    def init(self):

        session = self.start_session()
        # self.get)inventory
        # Create site
        self.import_batfish(session)
        session.commit()

    def import_batfish(self, session):

        # CURRENT_DIRECTORY = os.getcwd().split("/")[-1]
        NETWORK_NAME = "network-importer"
        SNAPSHOT_NAME = "latest"
        SNAPSHOT_PATH = "configs"

        bf_params = dict(host="localhost", port_v1=9997, port_v2=9996, ssl=False,)

        self.bf = Session.get("bf", **bf_params)
        self.bf.verify = False
        self.bf.set_network(NETWORK_NAME)
        self.bf.init_snapshot(SNAPSHOT_PATH, name=SNAPSHOT_NAME, overwrite=True)

        self.bf.set_snapshot(SNAPSHOT_NAME)

        self.import_batfish_device(session)
        self.import_batfish_cable(session)

    def import_batfish_device(self, session):
        """Import all devices from Batfish

        Args:
            session: sqlalquemy session
        """
        devices = self.bf.q.nodeProperties().answer().frame()

        for _, dev in devices.iterrows():

            session.add(self.device(name=dev["Node"],))
            logger.debug(f"Add device {dev['Node']}")

        logger.debug(f"Found {len(devices)} devices in Batfish")

        devices = session.query(self.device).all()
        logger.debug(f"Found {len(devices)} devices in memory")

        # -------------------------------------------------------------
        # Import Device, Interface & IPs
        # -------------------------------------------------------------
        for dev in devices:
            self.import_batfish_interface(dev, session)

    def import_batfish_interface(self, device, session):

        intfs = self.bf.q.interfaceProperties(nodes=device.name).answer().frame()

        for _, intf in intfs.iterrows():
            session.add(
                self.interface(
                    name=intf["Interface"].interface,
                    device_name=device.name,
                    description=intf["Description"],
                )
            )

            for prefix in intf["All_Prefixes"]:
                session.add(
                    self.ip_address(
                        address=prefix,
                        device_name=device.name,
                        interface_name=intf["Interface"].interface,
                    )
                )

        logger.debug(f"Found {len(intfs)} interfaces in netbox for {device.name}")

    def import_batfish_ip_address(self):
        pass

    def import_batfish_cable(self, session):

        p2p_links = self.bf.q.layer3Edges().answer()
        existing_cables = []
        for link in p2p_links.frame().itertuples():

            cable = self.cable(
                device_a_name=link.Interface.hostname,
                interface_a_name=re.sub(r"\.\d+$", "", link.Interface.interface),
                device_z_name=link.Remote_Interface.hostname,
                interface_z_name=re.sub(r"\.\d+$", "", link.Remote_Interface.interface),
            )
            uid = cable.unique_id()

            if uid not in existing_cables:
                session.add(cable)
                existing_cables.append(uid)

        nbr_cables = session.query(self.cable).count()
        logger.debug(f"Found {nbr_cables} cables in Batfish")

