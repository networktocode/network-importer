
# Architecture

Internally the network-importer is leveraging the [diffsync](https://github.com/networktocode/diffsync) library to compare the state of the network and the state of the Source of Truth. The diffsync library is designed to compare the state of 2 "adapters" based on a shared data-models.

To communicate to the network devices, the network importer is leveraging `Nornir` and incorporate a concept of drivers to let the user define their own method to communicate to the devices.
By default the network-importer supports 3 main actions to execute against the network devices:
- get_config
- get_neighbors
- get_vlans
For each action, there is a specific Nornir processor define

## Internal Datamodel

The internal/shared datamodel is defined in the [network_importer/models.py] file. Currently the following models are defined
- Site
- Device 
- Interface 
- IP address
- Prefix
- Vlan
- Cable

It's possible to extend the defualt models and add your own, please check the extensibility section of the doc

## Adapters

To operate the network importer needs 2 adapters. An adapter to read the information from the network and one to read/write information to Netbox via its Rest API are provided by default but it's possible to provide your own adapter or extend either of both default adapters.

The base adapter for Network-Importer is defined in `network_importer/XXX.py`. the main difference with a standard diffsync adapter is that a network-importer adapter needs to access a nornir inventory as parameters at init time (nornir).

### Netbox API Adapter

The NetBox API adapter is defined to read the status of a netbox server over its rest API and update Netbox based on the status of the network.

| Model            | Inherit from | Create | Read   | Update | Delete |
|------------------|--------------|--------|--------|--------|--------|
| NetboxSite       | Site         | No     | Yes    | No     | No     | 
| NetboxDevice     | Device       | No     | Yes    | No     | No     | 
| NetboxInterface  | Interface    | Yes    | Yes    | Yes    | Yes    | 
| NetboxIPAddress  | IPAddress    | Yes    | Yes    | Yes    | Yes    | 
| NetboxPrefix     | Prefix       | Yes    | Yes    | Yes    | No     | 
| NetboxVlan       | Vlan         | Yes    | Yes    | Yes    | No     | 
| NetboxCable      | Cable        | Yes    | Yes    | No     | No     | 


### Network Importer Adapter

The Network Importer Adapter is designed to read the status of the network primarily from Batfish but it can also leverage nornir to read few additional information like the list of LLDP/neighbors or the list of vlans

## Drivers


- get_config
- get_neighbors
- get_vlans