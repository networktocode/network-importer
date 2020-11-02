# Network Importer

The network importer is a tool/library to analyze and/or synchronize an existing network with a Network Source of Truth (SOT), it's designed to be idempotent and by default it's only showing the difference between the running network and the remote SOT. 

The main use cases for the network importer: 
 - Import an existing network into a SOT (Netbox) as a first step to automate a brownfield network
 - Check the differences between the running network and the Source of Truth

## Quick Start

- [Getting Started](docs/getting_started.md)
- [Configuration file](docs/configuration.md)
- [Supported Features and Architecture](docs/architecture.md)
- [Extensibility](docs/extensibility.md)

## How does it work

The Network Importer is using different tools to collect information from the network devices: 
- [batfish](https://github.com/batfish/batfish) to parse the configurations and extract a vendor neutral data model. 
- [nornir], [napalm], [netmiko] and [ntc-templates] to extract some information from the device cli if available
