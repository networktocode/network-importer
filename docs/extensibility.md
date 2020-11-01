

# Extend an existing adapter or provide your own


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
The easiest solution is to build a simple python package that will allow you to load adapter from anywhere.
Once your adapter is installed, you need to update your configuration file to indicate to the network-importer which adapter it should use.

```toml
[adapters]
network_class = "my_python_package.adapters.MyAdapter"
sot_class = "my_python_package.adapters.MyOtherAdapter"
```

# Extend the default datamodel


# Extend the default drivers
