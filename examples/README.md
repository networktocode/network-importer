
# Examples

## Spine Leaf 01

This example is based on a multi-vendor spine-leaf network composed of `junos`, `iosxr` and `eos` devices.

## Multi Site 02
This example is based on a multi-vendor network, organized in 3 sites : `sjc`, `hou` and `nyc` and is composed of `junos`, `iosxr`, `iosxe`, `nxos` and `eos` devices. 

Most of the topology is using point-2-point links and the server facing interfaces on the leafs are configured in L2 with local vlans.

## How to Get started

Each example directory includes everything you need to get started.

### Ensure you have a Netbox Server running

You must provide the address of a running Netbox Server (2.8 or 2.9) and a valid token via environment variables.
```
export NETBOX_ADDRESS=<Address to your netbox server>
export NETBOX_TOKEN=<Valid Netbox token>
```

If you currently don't have a compatible Netbox server available, or if you prefer to create a new one for this test, you can quickly get a server up and running by leveraging the `netbox-docker` project.
https://github.com/netbox-community/netbox-docker

### Ensure you have a Batfish server running

By default the network importer will try to connect to Batfish on the same host (localhost).
If you Batfish server is running on another system, you need to provide its address via environment variables.
```
export BATFISH_ADDRESS=10.0.1.2
```

### Populate Initial Data in Netbox with Ansible

For the network importer to work properly the devices must be already present in NetBox. 
To help with this example an ansible playbook is available to automatically populate NetBox with all required information.

#### Install Ansible and the Netbox collection from Galaxy
```
pip install ansible
ansible-galaxy collection install netbox.netbox
```

If needed you can define the path to your python interpreter with the environment variable `ANSIBLE_PYTHON_INTERPRETER` 
```
export ANSIBLE_PYTHON_INTERPRETER=<path to python>
```

#### Load all data in NetBox

To load all data in NetBox, execute the following playbook.
```
ansible-playbook pb.netbox_setup.yaml
```

It will create all required objects : `site`, `manufacturer`, `role`, `platform` and `device` if they don't already exist

### Install the network-importer

you need to install the network importer from pypi or install it from the local file
```
pip install network-importer
```
or
```
poetry install
```

### Execute

First run the network importer in check mode to see the differences between the SOT and the network : `network-importer check`
The first time this command will return a list of all devices and all interfaces because none of them exist in the SOT yet.

Next you can import everything by running : `network-importer apply`. This will create all interfaces, IP addresses,  prefixes and cables in Netbox.

At this point the network and the SOT are in sync and you can start "playing" with it. you can make some changes either to the configuration or to the SOT, like Adding or deleting an interface in NetBox, and observe the behavior when running the network importer in `check` or `apply` mode.