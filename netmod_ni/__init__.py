import re
import logging
from pybatfish.client.session import Session
from netmod import NetMod

logger = logging.getLogger("network-importer")


class NetModNi(NetMod):

    # site = NetboxSite
    # device = NetboxDevice
    # interface = NetboxInterface
    # ip_address = NetboxIPAddress
    # cable = NetboxCable

    def init(self):

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

        session = self.start_session()
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

            intfs = self.bf.q.interfaceProperties(nodes=dev.name).answer().frame()

            for _, intf in intfs.iterrows():
                session.add(
                    self.interface(
                        name=intf["Interface"].interface,
                        device_name=dev.name,
                        description=intf["Description"],
                    )
                )

                for prefix in intf["All_Prefixes"]:
                    session.add(
                        self.ip_address(
                            address=prefix,
                            device_name=dev.name,
                            interface_name=intf["Interface"].interface,
                        )
                    )

            logger.debug(f"Found {len(intfs)} interfaces in netbox for {dev.name}")

        # -------------------------------------------------------------
        # Import Cables
        # -------------------------------------------------------------
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

        session.commit()
