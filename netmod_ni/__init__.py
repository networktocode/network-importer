
import re
import logging
from pybatfish.client.session import Session
from netmod import NetMod

logger = logging.getLogger("network-importer")

# ============== INTERFACE =======================================
# Interface                         austin[GigabitEthernet0/0/0/0]
# Access_VLAN                                                 None
# Active                                                      True
# All_Prefixes                                     ['10.0.0.1/30']
# Allowed_VLANs
# Auto_State_VLAN                                             True
# Bandwidth                                                  1e+09
# Blacklisted                                                False
# Channel_Group                                               None
# Channel_Group_Members                                         []
# DHCP_Relay_Addresses                                          []
# Declared_Names                        ['GigabitEthernet0/0/0/0']
# Description                                                 None
# Encapsulation_VLAN                                          None
# HSRP_Groups                                                   []
# HSRP_Version                                                None
# Incoming_Filter_Name                                        None
# MLAG_ID                                                     None
# MTU                                                         1500
# Native_VLAN                                                 None
# Outgoing_Filter_Name                                        None
# PBR_Policy_Name                                             None
# Primary_Address                                      10.0.0.1/30
# Primary_Network                                      10.0.0.0/30
# Proxy_ARP                                                   True
# Rip_Enabled                                                False
# Rip_Passive                                                False
# Spanning_Tree_Portfast                                     False
# Speed                                                      1e+09
# Switchport                                                 False
# Switchport_Mode                                             NONE
# Switchport_Trunk_Encapsulation                             DOT1Q
# VRF                                                      default
# VRRP_Groups                                                   []
# Zone_Name                                                   None

class NetModNi(NetMod):

    # site = NetboxSite
    # device = NetboxDevice
    # interface = NetboxInterface
    # ip_address = NetboxIPAddress
    # cable = NetboxCable

    def import_data(self):

        # CURRENT_DIRECTORY = os.getcwd().split("/")[-1]
        NETWORK_NAME = "network-importer"
        SNAPSHOT_NAME = "latest"
        SNAPSHOT_PATH = "configs"

        bf_params = dict(
            host="localhost",
            port_v1=9997,
            port_v2=9996,
            ssl=False,
        )

        self.bf = Session.get("bf", **bf_params)
        self.bf.verify = False
        self.bf.set_network(NETWORK_NAME)
        self.bf.init_snapshot(SNAPSHOT_PATH, name=SNAPSHOT_NAME, overwrite=True)

        self.bf.set_snapshot(SNAPSHOT_NAME)

        session = self.start_session()
        devices = self.bf.q.nodeProperties().answer().frame()

        for _, dev in devices.iterrows():

            session.add(
                self.device(
                    name=dev["Node"], 
                )
            )  
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
                            interface_name=intf["Interface"].interface
                        )
                    )

            logger.debug(f"Found {len(intfs)} interfaces in netbox for {dev.name}")

        # -------------------------------------------------------------
        # Import Cables
        # -------------------------------------------------------------
        p2p_links = self.bf.q.layer3Edges().answer()
        for link in p2p_links.frame().itertuples():

            session.add(
                self.cable(
                    device_a_name=link.Interface.hostname,
                    interface_a_name=re.sub(r"\.\d+$", "", link.Interface.interface),
                    device_z_name=link.Remote_Interface.hostname,
                    interface_z_name=re.sub(r"\.\d+$", "", link.Remote_Interface.interface),
                )
            )

        nbr_cables = session.query(self.cable.id).count()
        logger.debug(f"Found {nbr_cables} cables in netbox")

        session.commit()

