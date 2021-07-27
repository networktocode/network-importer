
# Architecture

Internally the network-importer is leveraging the [diffsync](https://github.com/networktocode/diffsync) library to compare the state of the network and the state of the Source of Truth. [The diffsync library is designed to compare the state of 2 **adapters** based on a shared data-models](https://blog.networktocode.com/post/intro-to-diffing-and-syncing-data-with-diffsync/).

To communicate to the network devices, the network importer is leveraging [Nornir](https://github.com/nornir-automation/nornir) and incorporate a concept of **drivers** to easily add support for more platforms if needed.
By default the Network Importer supports 3 main actions to execute against the network devices:
- `get_config`: Retrieve the running configuration and store it in the `config_directory` folder.
- `get_neighbors`: Retrieve the list of all neighbors, either from LLDP or CDP (based on the configuration)
- `get_vlans`: Retrieve the list of vlans present on the device.

## Internal Datamodel

The internal/shared datamodel is defined in the [network_importer/models.py](../network_importer/models.py) file. Currently the following models are defined
- Site
- Device 
- Interface 
- IP address
- Prefix
- Vlan
- Cable

> It's possible to extend the default models and add your own, please check the [extensibility section](extensibility.md) of the documentation

## Backend, Adapters & Inventory

To operate the Network Importer needs 1 inventory and 2 adapters:
- An inventory to get the list of devices to analyze and get the minimum information to connect to them (platform, address, cred
entials ..)
- One adapter to read the information from the network and one to read/write information to the Source of Truth backend.

Since the inventory is usually leveraging the SOT, the SOT adapter and the inventory are packaged into a **backend**. Both Nautobot and Netbox are supported as backend systems. When a specific backend is selected it will update both the SOT adapter and the inventory.
With or without leveraging the default backends, it's possible to provide your own adapter or extend one of the default adapters.

> The base adapter for Network Importer is defined in [network_importer/adapters/base.py](../network_importer/adapters/base.py). The main difference with a standard diffsync adapter is that a Network Importer adapter needs to accept a NetworkImporter inventory (based on a Nornir inventory) as parameters at init time (nornir).

### Nautobot API Adapter

The Nautobot API adapter is designed to read the status of a Nautobot server over its Rest API and update Nautobot based on the status of the network.

The table below present the capabilities in term of : Read, Create, Update and Delete supported for each model by the netbox_api adapter.

| Model              | Inherit from | Create | Read   | Update | Delete |
|--------------------|--------------|--------|--------|--------|--------|
| NautobotSite       | Site         | No     | Yes    | No     | No     | 
| NautobotDevice     | Device       | No     | Yes    | No     | No     | 
| NautobotInterface  | Interface    | Yes    | Yes    | Yes    | Yes    | 
| NautobotIPAddress  | IPAddress    | Yes    | Yes    | Yes    | Yes    | 
| NautobotPrefix     | Prefix       | Yes    | Yes    | Yes    | No     | 
| NautobotVlan       | Vlan         | Yes    | Yes    | Yes    | No     | 
| NautobotCable      | Cable        | Yes    | Yes    | No     | No     | 

> It's possible to extend the default models and add your own, please check the [extensibility section](extensibility.md) of the documentation

### NetBox API Adapter

The NetBox API adapter is designed to read the status of a NetBox server over its Rest API and update NetBox based on the status of the network.

The table below present the capabilities in term of : Read, Create, Update and Delete supported for each model by the netbox_api adapter.

| Model            | Inherit from | Create | Read   | Update | Delete |
|------------------|--------------|--------|--------|--------|--------|
| NetboxSite       | Site         | No     | Yes    | No     | No     | 
| NetboxDevice     | Device       | No     | Yes    | No     | No     | 
| NetboxInterface  | Interface    | Yes    | Yes    | Yes    | Yes    | 
| NetboxIPAddress  | IPAddress    | Yes    | Yes    | Yes    | Yes    | 
| NetboxPrefix     | Prefix       | Yes    | Yes    | Yes    | No     | 
| NetboxVlan       | Vlan         | Yes    | Yes    | Yes    | No     | 
| NetboxCable      | Cable        | Yes    | Yes    | No     | No     | 

> It's possible to extend the default models and add your own, please check the [extensibility section](extensibility.md) of the documentation

### Network Importer Adapter

The Network Importer Adapter is designed to read the status of the network primarily from Batfish but it can also leverage Nornir to gather some additional information like the list of LLDP/CPD neighbors or the list of vlans.

## Drivers

The communicate with the network devices, the network-importer is leveraging Nornir and support some drivers per platform to easily support more device type.

Each driver, should support each of the following actions: 
- `get_config`: Retrieve the running configuration and store it in the `config_directory` folder.
- `get_neighbors`: Retrieve the list of all neighbors, either from LLDP or CDP (based on the configuration)
- `get_vlans`: Retrieve the list of vlans present on the device.

By default, 4 drivers are available `default`, `cisco_default`, `juniper_junos` & `arista_eos` and the mapping between a platform and the specific driver can be defined in the configuration. By default the 5 most common platforms are mapped to the following drivers.

| Platform        | Driver         | 
|-----------------|----------------|
| all             | default        | 
| cisco_nxos      | cisco_default  |
| cisco_ios       | cisco_default  |
| cisco_xr        | cisco_default  |
| juniper_junos   | juniper_junos  |
| arista_eos      | arista_eos     |

> The name of the platform must match the name of the slug platform defined in the inventory for a given device

### Drivers available by default

Each driver can implement an action using the connection of its choice. The table below present how each driver shipping with the network importer are implemented. 

| Driver            | get_config   | get_neighbors   | get_vlans       |
|-------------------|--------------|-----------------|-----------------|
| default           | Napalm       | Napalm          | Not Supported   | 
| default_cisco     | Netmiko      | Netmiko + Genie | Netmiko + Genie | 
| juniper_junos     | default      | default         | Not Supported   | 
| arista_eos        | default      | default         | Napalm + eAPI   |

> The name of the Napalm driver for each device must be defined in Netbox as part of the platform definition.