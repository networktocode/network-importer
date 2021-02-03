# Configuration File

By default the network importer will try to load a configuration file name `network_importer.toml`, this configuration file is not mandatory as long as the required information to connect to NetBox, Batfish and/or the network devices are provided via environment variables.

It's possible to specify which configuration file should be used in cli with the option `--config`.

The configuration file is organized in 8 sections detailed below. 

## Main Section

The main section included the main parameters to define what will be imported from the network and/or the SOT, where the configuration files are available/should be stored and how many number of tasks can be executed in parallel.

```toml
[main]
import_ips = true 
import_prefixes = false
import_intf_status = false

# Vlans (name, vlan-id) can be imported from the configuration, from the CLI or both 
# - "config" will import the vlans just from the configuration
# - "cli" will import the vlans from the cli using the action `get_vlans`
# - "true" will import vlans from both cli and config
# - no or false will not import any vlans
# The association between interface and vlans will always be derived from the configuration.
import_vlans = "config"         # Valid options are ["cli", "config", "no", true, false]

# Cabling can be imported from LLDP, CDP or the configuration (for some point to point links)
# - "lldp" or "cdp" will import the vlans from the cli using the action `get_neighbors`
# - "config" will import the neighbors from the configuration (for point to point links)
# - "true" will import neighbors from both cli and config 
# - no or false will not import any neighbors
import_cabling = "lldp"         # Valid options are ["lldp", "cdp", "config", "no", true, false]
excluded_platforms_cabling = ["cisco_asa"]

# Number of Nornir tasks to execute at the same tim
nbr_workers= 25

# Directory where the configuration can be find, organized in Batfish format
configs_directory = "configs"
```

# NetBox Section

The `[netbox]` section regroup all parameters to connect to NetBox and it also include an optional list of supported platforms.

```toml
[netbox]
address = "http://localhost:8080"                   # Alternative Env Variable : NETBOX_ADDRESS
token = "113954578a441fbe487e359805cd2cb6e9c7d317"  # Alternative Env Variable : NETBOX_TOKEN
verify_ssl = true                                   # Alternative Env Variable : NETBOX_VERIFY_SSL

# Define a list of supported platform, 
# if defined all devices without platform or with a different platforms will be removed from the inventory
supported_platforms = [ "cisco_ios", "cisco_nxos" ]
```

## Batfish Section

The `[batfish]` section regroup all parameters to connect to Batfish.
```toml
[batfish]
address = "localhost"   # Alternative Env Variable : BATFISH_ADDRESS
api_key = "XXXX"        # Alternative Env Variable : BATFISH_API_KEY
network_name = "network-importer"
snapshot_name = "latest"
port_v1 = 9997
port_v2 = 9996
use_ssl = false
api_key = "XXXX"       # API KEY to connect to Batfish enterprise instance
```

## Network Section

To be able to pull live information from the devices, the credential information needs to be provided either in the configuration file or as environment variables.

It's also possible to define some connection parameters for Netmiko and define a list of expected FDQNs that can be found in the network.

```toml
[network]
login = "username"          # Alternative Env Variable : NETWORK_DEVICE_LOGIN
password = "password"       # Alternative Env Variable : NETWORK_DEVICE_PWD
enable = true               # Alternative Env Variable : NETWORK_DEVICE_ENABLE

# Connection parameters for Netmiko 
global_delay_factor = 5
banner_timeout = 15
conn_timeout = 5

# List of valid FQDN that can be found in the network,
# The FQDNs in this list will be automatically removed from all neighbors discovered from LLDP/CDP
fqdns = [ ]
```

## Inventory Section

Define what method should be used to connect to the network devices. 

```toml
[inventory]
# The default method is to use the primary IP defined in NetBox.
# As an alternative it's possible to use the name of the device and provide your own FQDN.
use_primary_ip = false (default: true)
fqdn = "mydomain.com"

# Optional filter to limit the scope of the inventory, takes a comma separated string of key value pair"
filter = "site=XXX,site=YYY,status=active"    # Alternative Env Variable : INVENTORY_FILTER

# Configure what Inventory will be loaded bu the network importer.
inventory_class = "network_importer.inventory.NetboxInventory"
```

## Adapters Section

Configure which adapters will be loaded by the network importer.
Please see the [extensibility section](extensibility.md) of the documentation for more details on how to create your own adapter.

```toml
[adapters]
network_class = "network_importer.adapters.network_importer.adapter.NetworkImporterAdapter"
sot_class = "network_importer.adapters.netbox_api.adapter.NetBoxAPIAdapter"
```

## Drivers Section

Configure which driver to use for a given platform.
Please see the [extensibility section](extensibility.md) of the documentation for more details on how to create your own driver.

```toml
[drivers.mapping]
default = "network_importer.drivers.default"
cisco_nxos = "network_importer.drivers.cisco_default"
cisco_ios = "network_importer.drivers.cisco_default"
cisco_xr = "network_importer.drivers.cisco_default"
juniper_junos = "network_importer.drivers.juniper_junos"
arista_eos = "network_importer.drivers.arista_eos"
```

## Logs Section

Control how the application is generating logs.

```toml
[logs]
# Control the level of the logs printed to the console.
level = "info"        # "debug", "info", "warning"

# For each run, a performance log can be generated to capture how long
# some functions took to execute
performance_log = false
performance_log_directory = "performance_logs"
```