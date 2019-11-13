import toml
import os.path
from pathlib import Path
from jsonschema import Draft7Validator, validators
from . import schema

def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(
            validator, properties, instance, schema,
        ):
            yield error

    return validators.extend(
        validator_class, {"properties" : set_defaults},
    )


def load_config(config_file_name):
    global main, logs, netbox, batfish, network

    if not os.path.exists(config_file_name):
        raise Exception(f"Unable to find the configuration file {config_file_name}")
    
    config_string = Path(config_file_name).read_text()
    config = toml.loads(config_string)

    env_netbox_address = os.environ.get("NETBOX_ADDRESS", None)
    env_netbox_token = os.environ.get("NETBOX_TOKEN", None)
    env_batfish_address = os.environ.get("BATFISH_ADDRESS")

    # TODO need to refactor this section to avoid code duplication

    if env_netbox_address:
        config['netbox']['address'] = env_netbox_address
    elif "address" not in config['netbox'].keys():
        print("Netbox address is mandatory, please provide it either via the NETBOX_ADDRESS environement variable or in the configuration file")
        exit(1)
    
    if env_netbox_token:
        config['netbox']['token'] = env_netbox_token
    elif "token" not in config['netbox'].keys():
        print("Netbox Token is mandatory, please provide it either via the NETBOX_TOKEN environement variable or in the configuration file")
        exit(1)

    env_network_login = os.environ.get("NETWORK_DEVICE_LOGIN", None)
    env_network_password = os.environ.get("NETWORK_DEVICE_PWD", None)

    # TODO need to refactor this section to avoid code duplication

    if 'network' not in config:
        config["network"] = {}
        
    if env_network_login:
        config['network']['login'] = env_network_login
    
    if env_network_password:
        config['network']['password'] = env_network_password

    if env_batfish_address:
        config['batfish']['address'] = env_batfish_address
    
    ## Extend the jsonschema validator to insert the default values not provided
    DefaultValidatingDraft7Validator = extend_with_default(Draft7Validator)

    try:
        DefaultValidatingDraft7Validator(schema.config_schema).validate(config)
    except Exception as e:
        print(f"Configuration file ({config_file_name}) is not valid")
        print(e)
        exit(1)

    main = config['main']
    logs = config['logs']
    netbox = config['netbox']
    network = config['network']
    batfish = config['batfish']

    

