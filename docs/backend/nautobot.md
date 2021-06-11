
# Nautobot Backend

The Nautobot backend is composed of an inventory and a SOT adapter designed to work with Nautobot 1.0+.
Both the inventory and the SOT adapter can accept some specific settings as described below.

## Inventory

### Available Settings

```toml
[inventory.settings]

address = "http://localhost:8080"                   # Alternative Env Variable : NAUTOBOT_ADDRESS
token = "113954578a441fbe487e359805cd2cb6e9c7d317"  # Alternative Env Variable : NAUTOBOT_TOKEN
verify_ssl = true                                   # Alternative Env Variable : NAUTOBOT_VERIFY_SSL


# The default method is to use the primary IP defined in Nautobot.
# As an alternative it's possible to use the name of the device and provide your own FQDN.
use_primary_ip = false (default: true)
fqdn = "mydomain.com"

# Optional filter to limit the scope of the inventory, takes a comma separated string of key value pair"
filter = "site=XXX,site=YYY,status=active"    # Alternative Env Variable : INVENTORY_FILTER
```

## SOT Adapter

### Available Settings
```toml
[adapters.sot_settings]
# Settings for applying diffsync flags to diffsync model objects, in order to alter 
# the underlying sync behaviour. The model_flag is applied to any objects that have a 
# tag assigned within model_flag_tags. Further details on model_flags can be found 
# at: https://github.com/networktocode/diffsync/blob/269df51ce248beaef17d72374e96d19e6df95a13/diffsync/enum.py
model_flag_tags = ["your_tag"]
model_flag = 1 # flag enum int() representation
```