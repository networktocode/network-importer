
# Upgrade procedures

For all upgrade, it's mandatory to upgrade all dependencies and to validate what is the recommended version of Batfish. Please refer to the individual sections below for specific instructions.

## Upgrade from 2.0 to 3.0

The format of the configuration has changed between version 2.0 and 3.0.
Please check the new format of the configuration and see below some pointers to convert your configuration file to the new format.

### Update your configuration file
#### main 
- `backend` is now a mandatory setting in the configuration. 

#### inventory section
`fqdn`, `filter` and `use_primary_ip` have been removed from the inventory section, these settings are now part of the Netbox & Nautobot inventory settings, available under `[inventory.settings]`.
`supported_platforms` has been moved to the `[inventory]` section, it was previously under `[netbox]`

A new section [inventory.settings] is available and everything in this section will be passed to the inventory class at runtime. This allow each inventory to define and validate its own settings. The settings for the [nautobot inventory](backend/nautobot.md) and for the [netbox inventory](backend/netbox.md) are available in their respective documentation.

#### network section

`global_delay_factor`, `banner_timeout` and `conn_timeout` have been removed from the network section, these settings can now be define within the `[network.netmiko_extras]` section. The idea is to provide a less opinionated system that can accept any extras parameters for Netmiko and/or Naplam.
A similar section `[network.napalm_extras]` is available for napalm as well.

If you want to conserve the same settings that were defined in 2.0, you can add this few lines to your configuration
```toml
[network.netmiko_extras]
global_delay_factor = 15
banner_timeout = 5
conn_timeout = 5
```

#### netbox section

The `[netbox]` section has been removed from the main configuration and has been slitted into 2 new sections in the configuration. `[inventory.settings]` for anything related to the inventory and `adapters.sot_settings` for anything related to the adapter itself, please check the configuration of the [netbox_api adapter](backend/netbox.md) for more information.

#### adapters section
- `network_params` has been renamed to `network_settings`
- `sot_params` has been renamed to `sot_settings`