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

# -----------------------------------------------------------------------------
#                                 GLOBALS
# -----------------------------------------------------------------------------

main = None
logs = None
netbox = None
batfish = None
network = None


DEFAULT_CONFIG_FILE_NAME = "network_importer.toml"


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
        for property_name, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property_name, set_valule)

        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return validators.extend(validator_class, {"properties": set_defaults})


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

    # -------------------------------------------------------------------------
    #                                netbox
    # -------------------------------------------------------------------------

    # Read Netbox configuration from the provided file, or default to the
    # alternate environment variables.

    netbox = config.setdefault("netbox", {})

    nb_address = netbox.setdefault('address', os.environ.get("NETBOX_ADDRESS"))
    nb_token = netbox.setdefault('token', os.environ.get("NETBOX_TOKEN"))

    # validate that the NetBox address and token are provided.  If not, print
    # an error and exit with error code 1

    if not nb_address:
        print(
            "Netbox address is mandatory, please provide it either via the "
            "NETBOX_ADDRESS environement variable or in the configuration file"
        )
        exit(1)

    if not nb_token:
        print(
            "Netbox Token is mandatory, please provide it either via the "
            "NETBOX_TOKEN environement variable or in the configuration file"
        )
        exit(1)

    # cacert and verify_ssl are optional is optional

    if 'cacert' not in netbox and 'NETBOX_CACERT' in os.environ:
        netbox['cacert'] = os.environ['NETBOX_CACERT']

    if 'verify_ssl' not in netbox and 'NETBOX_VERIFY_SSL' in os.environ:
        netbox['verify_ssl'] = os.environ['NETBOX_VERIFY_SSL']

    # -------------------------------------------------------------------------
    #                                batfish
    # -------------------------------------------------------------------------

    batfish = config.setdefault('batfish', {})
    batfish.setdefault('address', os.environ.get("BATFISH_ADDRESS"))

    # -------------------------------------------------------------------------
    #                                network
    # -------------------------------------------------------------------------

    network = config.setdefault('network', {})
    network.setdefault('login', os.environ.get("NETWORK_DEVICE_LOGIN"))
    network.setdefault('password', os.environ.get("NETWORK_DEVICE_PWD"))

    # -------------------------------------------------------------------------
    # validate the config structure using the JSON schema defined in the
    # `schama` module.  This process will also set the default values to the
    # configuration properties if they are not provided either in the config
    # file or alternate environment variables.
    # -------------------------------------------------------------------------

    default_validator = extend_with_default(Draft7Validator)

    try:
        default_validator(schema.config_schema).validate(config)
    except Exception as e:
        print(f"Configuration file ({config_file_name}) is not valid")
        print(e)
        exit(1)

    # since the code will open a netbox connection in multiple places,
    # store the actual value provided to the pynetbox.Api, which is
    # also the underlying requests.Session.verify value, as documented
    # https://requests.readthedocs.io/en/master/user/advanced/#ssl-cert-verification

    netbox['request_ssl_verify'] = netbox.get('cacert') or netbox['verify_ssl']

    main = config["main"]
    logs = config["logs"]
