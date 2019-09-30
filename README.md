The network importer is a tool to import/synchronize an existing network with a Network Source of Truth, it's designed to be idempotent and by default it's only showing the difference between the running network and the central database. 

The main use cases for the network importer 
 - Import an existing network into a SOT (Netbox) as a first step to automate a brownfield network
 - Check the differences between the running network and the Source of Truth

# How to use 

The network importer can run either in `check` mode or in `apply` mode. 
 - In `check` mode, no modification will be made to the SOT, the differences will be printed on the screen
 - in `apply` mode, the SOT will be updated will all interfaces, IPs, vlans etc

## Start Batfish in a container

The network-importer requires to have access to a working batfish environment, you can easily start one using docker
```
docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish
```

## Setup your local environment

NETBOX_ADDRESS
NETBOX_TOKEN
BATFISH_ADDRESS (default: localhost)

# How does it work

The network importer is using [batfish](https://github.com/batfish/batfish) to parse the configurations extract a vendor neutral data model. 
All devices supported by batfish should be supported by the `network-importer`

# inputs
## Configs only
- Use batfish to parse the configuration
- If devices are present in netbox, deriv site information and try to import as much as possible

## Configs + Inventory (partially supported)
- Use batfish to parse the configuration
- Try to connect to the devices using nornit to pull the LLDP informations

## Inventory only (partially supported)
- Try to connect to the devices using nornit to pull the LLDP informations and the configs
- Parse the configs using Batfish
- If devices are not in netbox, attempt to create them with the information provided in the inventory

# disclaimer / Assumption

Currently the library only supports netbox but the idea for 1.0 is to support multiple backend SOT
Currently the assumption is that vlans are global to a site. need to find a way to provide more flexibility here without making it too complex

# TODO list

Add support for LAG
Add support for HSRP/VRRP
Add support for VRF
Add support for OSPF ( bfq.ospfAreaConfiguration() / )
Add support for BGP
Add support for SNMP
Add support for VXLAN/VNI
