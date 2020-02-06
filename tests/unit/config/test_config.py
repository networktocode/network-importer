# pylint: disable=C0121,C0116
import os
from os import path

import network_importer.config as config
from network_importer.config import env_var_to_bool

HERE = path.abspath(path.dirname(__file__))


def test_env_var_to_bool():

    assert env_var_to_bool(1) == True
    assert env_var_to_bool("1") == True
    assert env_var_to_bool("True") == True
    assert env_var_to_bool("true") == True
    assert env_var_to_bool("TRUE") == True
    assert env_var_to_bool(True) == True
    assert env_var_to_bool("Yes") == True
    assert env_var_to_bool("yes") == True
    assert env_var_to_bool("YES") == True

    assert env_var_to_bool(0) == False
    assert env_var_to_bool("0") == False
    assert env_var_to_bool("false") == False
    assert env_var_to_bool("False") == False
    assert env_var_to_bool("False") == False
    assert env_var_to_bool("no") == False
    assert env_var_to_bool("NO") == False
    assert env_var_to_bool("No") == False
    assert env_var_to_bool(False) == False


def test_config_no_config():

    config.load_config()
    assert config.netbox["address"] == "http://localhost"


def test_config_env_var_no_file():

    os.environ["NETBOX_ADDRESS"] = "http://envvar"
    os.environ["NETBOX_TOKEN"] = "mytoken"  # nosec
    os.environ["NETWORK_DEVICE_LOGIN"] = "mylogin"
    os.environ["NETWORK_DEVICE_PWD"] = "pypwd"  # nosec
    os.environ["NETBOX_VERIFY_SSL"] = "1"
    os.environ["NETBOX_CACERT"] = "mycert"

    config.load_config()
    assert config.netbox["address"] == "http://envvar"
    assert config.netbox["token"] == "mytoken"
    assert config.netbox["cacert"] == "mycert"
    assert config.netbox["verify_ssl"] == True

    assert config.network["login"] == "mylogin"
    assert config.network["password"] == "pypwd"


def test_config_env_var_file():

    os.environ["NETBOX_ADDRESS"] = "http://fromenv"
    os.environ["NETBOX_TOKEN"] = "fromenv"  # nosec
    os.environ["NETWORK_DEVICE_LOGIN"] = "fromenv"
    os.environ["NETWORK_DEVICE_PWD"] = "fromenv"  # nosec
    os.environ["NETBOX_VERIFY_SSL"] = "false"
    os.environ["NETBOX_CACERT"] = "fromenv"

    config.load_config(f"{HERE}/fixtures/config_env_var.toml")
    assert config.netbox["address"] == "http://fromenv"
    assert config.netbox["token"] == "fromenv"
    assert config.netbox["cacert"] == "fromenv"
    assert config.netbox["verify_ssl"] == False

    assert config.network["login"] == "fromenv"
    assert config.network["password"] == "fromenv"  # nosec


def test_config_nev_verify_ssl():

    os.environ["NETBOX_ADDRESS"] = "http://fromenv"
    os.environ["NETBOX_TOKEN"] = "fromenv"  # nosec
    os.environ["NETWORK_DEVICE_LOGIN"] = "fromenv"
    os.environ["NETWORK_DEVICE_PWD"] = "fromenv"  # nosec
    os.environ["NETBOX_VERIFY_SSL"] = "false"
    os.environ["NETBOX_CACERT"] = "fromenv"

    config.load_config(f"{HERE}/fixtures/config_env_var.toml")
    assert config.netbox["address"] == "http://fromenv"
    assert config.netbox["token"] == "fromenv"
    assert config.netbox["cacert"] == "fromenv"
    assert config.netbox["verify_ssl"] == False

    assert config.network["login"] == "fromenv"
    assert config.network["password"] == "fromenv"  # nosec
