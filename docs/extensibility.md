
# Extensibility

The network importer has been designed to be easily extended to support all corner cases and specific requirements.
The extensibility principles is inspired by Python class extensibility and will most-likely require to create your own python package to simplify how the network-importer can find your custom classes. 



## Extend the default drivers

A network-importer driver is a collection of Nornir tasks organized in a Class named `NetworkImporterDriver`.
You can create your own driver from scratch of you can inherit from the existing driver. 

Each driver must support 3 static methods, each accepting one parameter `task` : `get_config`, `get_neighbors` and `get_vlans`

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

It's possible to provide your own adapter or extend an existing by creating a new python class that either inherit from the base adapter or from an existing adapter.

```python
# Create a new Adapter
from network_importer.adapters.base import BaseAdapter

class MyAdapter(BaseAdapter):

    def load(self):
        pass
```


```python
# Extend an existing Adapter
from network_importer.adapters.network_importer.adapter import NetworkImporterAdapter

class MyAdapter(NetworkImporterAdapter):

    # if you extend an existing adapter 
    # you can add your own logic before/after every function by redefining any existing function 
    # and by calling super() 
    def validate_cabling(self):
        super().validate_cabling()
        # Add your own logic
```

Your adapters needs to be available within your python virtual environment.
The easiest solution is to build a simple python package that will allow you to load your adapter from anywhere.
Once your custom adapter is installed, you need to update your configuration file to indicate to the network-importer which adapter it should use.

```toml
[adapters]
network_class = "my_python_package.adapters.MyAdapter"
sot_class = "my_python_package.adapters.MyOtherAdapter"
```

## Extend the default models

It's possible to extend the default models by creating new classes and attaching them to your own adapter.

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
```

For this modification to take effect, the new adapter must be registered in the configuraiton file.
```toml
[adapters]
sot_class = "my_python_package.adapters.MyOtherAdapter"
```


### Extend the default site model (main attributes)

By default, all attributes on a model have a local significance and won't be ignored during a diff or a sync.
Only the attributes listed in `_attributes` will be used to during a diff or a sync as long as both models (from each adapter) share the same list of `_attributes`. 

Below is an example on how to add your own attribute to an existing list of attributes. Similar to the previous example, this model will need to be attached to an adapter, and a `asn` must be available as an attributes from both models for it to be effective. 

```python
# my_adapter/models.py
from network_importer.adapters.netbox_api.models import NetboxSite

class MySite(NetboxSite):
    
    _attributes = tuple(list(NetboxSite._attributes) + ["asn"])

    asn: Optional[int]
```


