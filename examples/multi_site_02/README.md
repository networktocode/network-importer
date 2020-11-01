
# Example Multi Site 2


## How to Get started

### Ensure you have a Netbox Server running

You must provide the address of a running Netbox Server (2.8 or 2.9) and a valid token via environment variables.
```
export NETBOX_ADDRESS=<Address to your netbox server>
export NETBOX_TOKEN=<Valid Netbox token>
```

If you currently don't have a compatible Netbox server available, or it you prefer to create a new one for this test, you can quickly get a server up and running by leveraging the `netbox-docker` project.
https://github.com/netbox-community/netbox-docker

### Ensure you have a Batfish server running

By default the network importer will try to connect to Batfish on the same host (localhost).
If you Batfish server is running on another system, you need to provide its address via environment variables.
```
export BATFISH_ADDRESS=10.0.1.2
```

### Populate Initial Data in Netbox with Ansible

For the network importer to work properly the devices must be already present in netbox. 
To help with this example an ansible playbook is available to automatically populate Netbox with all required information.

#### Install Ansible and the Netbox collection from Galaxy
```
pip install ansible
ansible-galaxy collection install netbox.netbox
```

If needed you can define the path to your python interpreter with the environment variable `ANSIBLE_PYTHON_INTERPRETER` 
```
export ANSIBLE_PYTHON_INTERPRETER=<path to python>
```

#### Load all data in Netbox

To load all data in Netbox, execute the following playbook.
```
ansible-playbook pb.netbox_setup.yaml
```

It will create the following objects if they don't already exist:
- manufacturers: ["juniper", "cisco", "arista"]
- device_roles: ["spine", "leaf", "router", ]
- platforms: ["junos", "iosxr", "ios", "nxos", "eos"]
- sites: ["hou", "nyc", "sjc"]
- all devices

### Run the network-importer

```
pip install network-importer
```

```
network-importer --check --diff
```