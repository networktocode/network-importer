To use this local branch:
```
git clone https://github.com/craigcpj/network-importer.git
pip install network-importer/
```
# Network Importer

The network importer is a tool/library to analyze and/or synchronize an existing network with a Network Source of Truth (SOT), it's designed to be idempotent and by default it's only showing the difference between the running network and the remote SOT.

The main use cases for the network importer:

- Import an existing network into a SOT (Nautobot or NetBox) as a first step to automate a brownfield network
- Check the differences between the running network and the Source of Truth

This application is intended to run __outside__ of Nautobot. 

![Architecture](docs/images/batfish_network_importer.png)

## Deprecation Notice

This application is being put into maintenance mode. Additional features may be implemented for Nautobot 1.x. The functionality for Nautobot is being moved to the [Device Onboarding](https://docs.nautobot.com/projects/device-onboarding/en/latest/) application for Nautobot 2.x. The last NetBox support was version 2.x.

## Quick Start

- [Getting Started](docs/getting_started.md)
- [Configuration file](docs/configuration.md)
- [Supported Features and Architecture](docs/architecture.md)
- [Extensibility](docs/extensibility.md)
- [Upgrade procedure](docs/upgrade.md)

## Questions

For any questions or comments, please feel free to open an issue or swing by the [networktocode slack channel](https://networktocode.slack.com/). (channel #networktocode)

Sign up [here](http://slack.networktocode.com/)
