
# Extensibility

The Network Importer has been designed to be easily extended to support all corner-cases and specific requirements.
The extensibility principles leverages Python object extensibility. It's recommend to create your own python package to simplify how your custom classes will be available within your virtual environment. 

You can use [setuptools](https://python-packaging-tutorial.readthedocs.io/en/latest/setup_py.html) or [Poetry](http://blog.networktocode.com/post/upgrade-your-python-project-with-poetry/) to quickly create a new python package.

There are different ways the Network Importer can be extended depending on what you are trying to achieve:
  - [Extend the default drivers](#extend-the-default-drivers)
  - [Extend an existing adapter or provide your own](#extend-an-existing-adapter-or-provide-your-own)
  - [Extend the default inventory](#extend-the-default-inventory)
  - [Extend the default models](#extend-the-default-models)

## Extend the default drivers

A Network Importer driver is a collection of Nornir tasks organized in a Class named `NetworkImporterDriver`.
You can create your own driver from scratch or you can inherit from the existing drivers. 

Each driver must support a static method per action, each accepting one parameter `task` : `get_config`, `get_neighbors` and `get_vlans`

Below is skeleton of driver that can be used as aa starting point. 

```python
# my_python_package/driver/my_driver.py

from nornir.core.task import Result, Task
from network_importer.drivers.default import NetworkImporterDriver as DefaultNetworkImporterDriver

class NetworkImporterDriver(DefaultNetworkImporterDriver):
    """Collection of Nornir Tasks specific to a given devices."""

    @staticmethod
    def get_config(task: Task) -> Result:
        """Get the latest configuration from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        pass

    @staticmethod
    def get_neighbors(task: Task) -> Result:
        """Get a list of neighbors from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the neighbors
            The format of the result but must be similar to Neighbors defined in network_importer.processors.get_neighbors
        """
        pass

    @staticmethod
    def get_vlans(task: Task) -> Result:
        """Get a list of vlans from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the vlans
            The format of the result but must be similar to Vlans defined in network_importer.processors.get_vlans
        """
        pass
```

To associate this driver with a given platform, you need to update the section `[drivers.mapping]` of the configuration as follow.
```toml
[drivers.mapping]
cisco_ios = "my_python_package.driver.my_driver" 
```

## Extend an existing adapter or provide your own

It's possible to provide your own adapter or extend an existing one by creating a new python class that either inherit from the base adapter or from an existing adapter.

###  Extend an existing Adapter

Extending one of the existing adapters can be useful to manage some user specific requirements that can't be incorporated into the main library.

The easier way to extend an adapter and add your own logic is to create a new class that will inherit from one of existing adapters and re-define the method that you would like to update. It's recommended to leverage `super()` to ensure that the original method is still executed.

```python
from network_importer.adapters.network_importer.adapter import NetworkImporterAdapter

class MyAdapter(NetworkImporterAdapter):

    # if you extend an existing adapter 
    # you can add your own logic before/after every function by redefining any existing function 
    # and by calling super() 
    def validate_cabling(self):
        super().validate_cabling()
        # Add your own logic
```

### Create a new adapter

All adapters must implement the `load` method. The load method is called during the initialization process and is expected to load all the data from the remote system into the local cache, following the Models defined.

```python
from network_importer.adapters.base import BaseAdapter

class MyAdapter(BaseAdapter):

    def load(self):
        pass
```

### Use your own adapter

Once your custom adapter is installed, you need to update your configuration file to indicate to the Network Importer which adapter it should use in the `adapter` section.

```toml
[adapters]
network_class = "my_python_package.adapters.MyAdapter"
sot_class = "my_python_package.adapters.MyOtherAdapter"
```

## Extend the default inventory

It's possible to extend the default inventory or provide your own inventory.

A Network Importer inventory must be a valid Nornir 3.x inventory and it must be based of the NetworkImporterInventory class.

Once you have created your own inventory, you need to register it with Nornir in order for Nornir to successfully load it. You than need to define your inventory name in [inventory.inventory_class]

## Extend the default models

It's possible to extend the default models by creating new classes and attaching them to an adapter.

Below is an example on how to add a new field ASN to the site Model and how to attach it to `MyAdapter` which itself inherits from the default `NetworkAPIAdapter`. 

### Extend the default site model (hidden attributes)
```python
# my_adapter/models.py
from network_importer.adapters.netbox_api.models import NetboxSite

class MySite(NetboxSite):
    asn: Optional[int]
```

#### Create a custom adapter to attach your custom model
```python
# my_python_package/adapter.py
from network_importer.adapters.netbox_api.adapter import NetworkAPIAdapter
from .models import MySite

class MyOtherAdapter(NetworkAPIAdapter):

    site = MySite

    def load(self):
        super().load()
        # Add your logic here to populate asn
```

For this modification to take effect, the new adapter must be registered in the configuration file.
```toml
[adapters]
sot_class = "my_python_package.adapters.MyOtherAdapter"
```

### Extend the default site model (main attributes)

By default, all attributes of a model have a local significance and will be ignored during a diff or a sync.
Only the attributes listed in `_attributes` will be used during a diff or a sync as long as both models (from each adapter) share the same list of `_attributes`. 

Below is an example on how to add your own attribute to an existing list of attributes. Similar to the previous example, this model will need to be attached to an adapter, and `asn` must be available as an attribute from both models for it to be effective. 

```python
# my_adapter/models.py
from network_importer.adapters.netbox_api.models import NetboxSite

class MySite(NetboxSite):

    _attributes = tuple(list(NetboxSite._attributes) + ["asn"])

    asn: Optional[int]
```


