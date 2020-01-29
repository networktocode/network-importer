"""
(c) 2019 Network To Code

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import toml
import os.path
from pathlib import Path
from jsonschema import Draft7Validator, validators
from . import schema


def extend_with_default(validator_class):
    """
    

    Args:
      validator_class: 

    Returns:

    """
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        """
        

        Args:
          validator: 
          properties: 
          instance: 
          schema: 

        Returns:

        """
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return validators.extend(validator_class, {"properties": set_defaults})


DEFAULT_CONFIG_FILE_NAME = "network_importer.toml"


def load_config(config_file_name=DEFAULT_CONFIG_FILE_NAME):
    """
    

    Args:
      config_file_name: (Default value = DEFAULT_CONFIG_FILE_NAME)

    Returns:

    """
    global main, logs, netbox, batfish, network

    if config_file_name == DEFAULT_CONFIG_FILE_NAME and not os.path.exists(
        config_file_name
    ):
        config = {}
    elif not os.path.exists(config_file_name):
        raise Exception(f"Unable to find the configuration file {config_file_name}")
    else:
        config_string = Path(config_file_name).read_text()
        config = toml.loads(config_string)

    env_netbox_address = os.environ.get("NETBOX_ADDRESS", None)
    env_netbox_token = os.environ.get("NETBOX_TOKEN", None)
    env_netbox_sslcert = os.environ.get("NETBOX_SSLCERT", False)        # yes False! by default
    env_batfish_address = os.environ.get("BATFISH_ADDRESS")

    # TODO need to refactor this section to avoid code duplication
    if "netbox" not in config:
        config["netbox"] = {}

    config['netbox']['sslcert'] = env_netbox_sslcert
    if env_netbox_address:
        config["netbox"]["address"] = env_netbox_address
    elif "address" not in config["netbox"].keys():
        print(
            "Netbox address is mandatory, please provide it either via the NETBOX_ADDRESS environement variable or in the configuration file"
        )
        exit(1)

    if env_netbox_token:
        config["netbox"]["token"] = env_netbox_token
    elif "token" not in config["netbox"].keys():
        print(
            "Netbox Token is mandatory, please provide it either via the NETBOX_TOKEN environement variable or in the configuration file"
        )
        exit(1)

    env_network_login = os.environ.get("NETWORK_DEVICE_LOGIN", None)
    env_network_password = os.environ.get("NETWORK_DEVICE_PWD", None)

    # TODO need to refactor this section to avoid code duplication

    if "network" not in config:
        config["network"] = {}

    if env_network_login:
        config["network"]["login"] = env_network_login

    if env_network_password:
        config["network"]["password"] = env_network_password

    if env_batfish_address:
        config["batfish"]["address"] = env_batfish_address

    ## Extend the jsonschema validator to insert the default values not provided
    DefaultValidatingDraft7Validator = extend_with_default(Draft7Validator)

    try:
        DefaultValidatingDraft7Validator(schema.config_schema).validate(config)
    except Exception as e:
        print(f"Configuration file ({config_file_name}) is not valid")
        print(e)
        exit(1)

    main = config["main"]
    logs = config["logs"]
    netbox = config["netbox"]
    network = config["network"]
    batfish = config["batfish"]
