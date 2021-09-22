
## Getting Started

### Install

The Network Importer can be installed from pypi or from a wheel

```
pip install network-importer
```

### Pre-requisite

To operate, the Network Importer is dependents on the following items:
- A device inventory (defined in Nautobot or NetBox for now)
- Batfish 
- A valid configuration file

#### Inventory

A device inventory must be already available in Nautobot or NetBox, if you don't have your devices in Nautobot or NetBox yet you can use the [onboarding plugin for Nautobot](https://github.com/nautobot/nautobot-plugin-device-onboarding) or the [onboarding plugin for NetBox](https://github.com/networktocode/ntc-netbox-plugin-onboarding/) to easily import your devices. 

To be able to connect to the device the following information needs to be defined :
- Primary ip address (or valid fqdn)
- Platform (must be a valid Netmiko driver or have a valid Napalm driver defined)

> Connecting to the device is not mandatory but some features depends on it: configuration update, mostly cabling and potentially vlan update.

##### Validate your inventory

You can validate the status of your inventory with the command `network-importer inventory --check-connectivity`

```
# network-importer inventory
                                           Device Inventory (all)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Device                     ┃ Platform      ┃ Driver                                 ┃ Reachable ┃ Reason                          ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ jcy-bb-01.infra.ntc.com    │ cisco_ios     │ network_importer.drivers.cisco_default │ True      │                                 │
│ jcy-rtr-01.infra.ntc.com   │ cisco_ios     │ network_importer.drivers.cisco_default │ True      │                                 │
│ jcy-rtr-02.infra.ntc.com   │ cisco_ios     │ network_importer.drivers.cisco_default │ True      │                                 │
│ jcy-spine-01.infra.ntc.com │ cisco_nxos    │ network_importer.drivers.cisco_default │ True      │                                 │
│ jcy-spine-02.infra.ntc.com │ cisco_nxos    │ network_importer.drivers.cisco_default │ True      │                                 │
│ nyc-bb-01.infra.ntc.com    │ juniper_junos │ network_importer.drivers.juniper_junos │ True      │                                 │
│ nyc-leaf-01.infra.ntc.com  │ arista_eos    │ network_importer.drivers.arista_eos    │ False     │ device not reachable on port 22 │
│ nyc-leaf-02.infra.ntc.com  │ arista_eos    │ network_importer.drivers.arista_eos    │ False     │ device not reachable on port 22 │
│ nyc-rtr-01.infra.ntc.com   │ juniper_junos │ network_importer.drivers.juniper_junos │ False     │ device not reachable on port 22 │
│ nyc-rtr-02.infra.ntc.com   │ juniper_junos │ network_importer.drivers.juniper_junos │ False     │ device not reachable on port 22 │
│ nyc-spine-01.infra.ntc.com │ arista_eos    │ network_importer.drivers.arista_eos    │ False     │ device not reachable on port 22 │
│ nyc-spine-02.infra.ntc.com │ arista_eos    │ network_importer.drivers.arista_eos    │ False     │ device not reachable on port 22 │
└────────────────────────────┴───────────────┴────────────────────────────────────────┴───────────┴─────────────────────────────────┘
```

> the option `--check-connectivity` will try to connect to all devices on port 22 (tcp_ping)

#### Batfish

The Network Importer requires to have access to a working batfish environment, you can easily start one using docker or use a Batfish Enterprise instance.

You can start a local batfish instance with the following command 
```
docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish:2020.10.08.667
```

#### Configuration file

The information to connect to NetBox must be provided either via environment variables or via the configuration file.
The configuration file below present the most standard options that can be provided to control the behavior of the Network Importer. 

Please check the [documentation of the configuration file](configuration.md) for the complete list of all options.

```toml
[main]
# import_ips = true 
# import_prefixes = false
# import_cabling = "lldp"       # Valid options are ["lldp", "cdp", "config", false]
# import_intf_status = false     # If set as False, interface status will be ignore all together
# import_vlans = "config"         # Valid options are ["cli", "config", true, false]
# excluded_platforms_cabling = ["cisco_asa"]

# Directory where the configurations can be find, organized in Batfish format
# configs_directory= "configs"

backend = "nautobot"            # Valid options are ["nautobot", "netbox"]

[inventory]
# Define a list of supported platform, 
# if defined all devices without platform or with a different platforms will be removed from the inventory
# supported_platforms = [ "cisco_ios", "cisco_nxos" ]

[inventory.settings]
# The information to connect to Nautobot needs to be provided, either in the config file or as environment variables
# These settings are specific to the Nautobot inventory, please check the documentation of your inventory for the 
# exist list of of available settings.
address = "http://localhost:8080"                   # Alternative Env Variable : NAUTOBOT_ADDRESS
token = "113954578a441fbe487e359805cd2cb6e9c7d317"  # Alternative Env Variable : NAUTOBOT_TOKEN
verify_ssl = true                                   # Alternative Env Variable : NAUTOBOT_VERIFY_SSL

[network]
# To be able to pull live information from the devices, the credential information needs to be provided
# either in the configuration file or as environment variables ( & NETWORK_DEVICE_PWD)
login = "username"      # Alternative Env Variable : NETWORK_DEVICE_LOGIN
password = "password"   # Alternative Env Variable : NETWORK_DEVICE_PWD

[batfish]
address= "localhost"    # Alternative Env Variable : BATFISH_ADDRESS
# api_key = "XXXX"      # Alternative Env Variable : BATFISH_API_KEY
# use_ssl = false

[logs]
# Define log level, currently the logs are printed on the screen
# level = "info" # "debug", "info", "warning"
```

### Execute

The Network Importer can run either in `check` mode or in `apply` mode. 
 - In `check` mode, no modification will be made to the SOT, the differences will be printed on the screen
 - in `apply` mode, the SOT will be updated will all interfaces, IPs, vlans etc

#### Check Mode

In check mode the Network Importer is working in read-only mode.

The first time, it's encouraged to run the Network Importer in `check` mode to guarantee that no change will be made to the SOT.

```
network-importer check [--update-configs] [--limit="site=nyc"]
```
This command will print on the screen a list of all changes that have been detected between the Network and the SOT.

#### Apply Mode

If you are confident with the changes reported in check mode, you can run the network importer in apply mode to update your SOT to align with your network. The Network Importer will attempt to create/update or delete all elements in the SOT that do not match what has been observed in the network.

```
network-importer apply [--update-configs] [--limit="site=nyc"]
```

> !! Running in Apply mode may result in loss of data in your SOT, as the network importer will attempt to delete all Interfaces and IP addresses that are not present in the network. !!
> Before running in Apply mode, it's highly encouraged to do a backup of your database.

## Development

In addition to the supplied command you can also use `docker-compose` to bring up the required service stack. Like so:
```
sudo docker-compose up -d
sudo docker-compose exec network-importer bash
sudo docker-compose down
```
