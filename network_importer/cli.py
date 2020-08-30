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
# pylint: disable=C0103,W0102,C0415,R1724,W0611,R1710,R1710,E1101,W0613,,C0413,R0904,E1120

import logging
import sys
import pdb
import click

import network_importer.config as config
from network_importer.utils import build_filter_params
from network_importer.main import NetworkImporter

import network_importer.performance as perf

from network_importer.adapters.netbox import NetBoxAdapter

__author__ = "Damien Garros <damien.garros@networktocode.com>"

logger = logging.getLogger("network-importer")


@click.command()
@click.version_option()
@click.option(
    "--config",
    "config_file",
    default="network_importer.toml",
    help="Network Importer Configuration file (TOML format)",
    type=str,
    show_default=True,
)
@click.option(
    "--limit",
    default=False,
    help="limit the execution on a specific device or group of devices --limit=device1 or --limit='site=sitea' ",
    type=str,
)
@click.option("--diff", is_flag=True, help="Show the diff for all objects")
@click.option("--apply", is_flag=True, help="Save changes in Backend")
@click.option(
    "--check",
    is_flag=True,
    help="Display what are the differences but do not save them",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Keep the script in interactive mode once finished for troubleshooting",
)
@click.option(
    "--update-configs", is_flag=True, help="Pull the latest configs from the devices"
)
def main(config_file, limit, diff, apply, check, debug, update_configs):
    config.load_config(config_file)
    perf.init()

    # ------------------------------------------------------------
    # Setup Logging
    # ------------------------------------------------------------
    logging.getLogger("pybatfish").setLevel(logging.ERROR)
    logging.getLogger("netaddr").setLevel(logging.ERROR)

    # if config.logs["level"] != "debug":
    logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)
    logging.getLogger("nornir.core.task").setLevel(logging.CRITICAL)

    logging.basicConfig(
        stream=sys.stdout, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # if config.logs["level"] == "debug":
    #     logger.setLevel(logging.DEBUG)
    # elif config.logs["level"] == "warning":
    #     logger.setLevel(logging.WARNING)
    # else:
    #     logger.setLevel(logging.INFO)

    logger.setLevel(logging.DEBUG)

    filters = {}
    build_filter_params(config.main["inventory_filter"].split((",")), filters)

    # print(filters)
    # filters["limit"] = 100

    logger.info(f"Import NetBox Model")
    nb = NetBoxAdapter()
    nb.init(
        url=config.netbox["address"],
        token=config.netbox["token"], # 1234567890abcdefghijklmnopqrstuvwxyz0123
        filters=filters
    )
    nb_session = nb.start_session()

    logger.info(f"Import NI Model")
    ni = NetworkImporter()
    ni.init(
        url=config.netbox["address"],
        token=config.netbox["token"], # 1234567890abcdefghijklmnopqrstuvwxyz0123
        filters=filters
    )
    ni_session = ni.start_session()

    # logger.info(f"Import Yaml Model")
    # yml = NetModYaml()
    # yml.init(directory="/Users/damien/projects/network-importer/examples/spine_leaf_yaml")
    # yml_session = yml.start_session()

    # nmnb.sync(nmni)

    # TODO add code to set config.main["hostvars_directory"] based on options.output
    # TODO add code to set config.main["configs_directory"] based on options.configs

    # ni = NetworkImporter()

    # if update_configs:
    #     ni.build_inventory(limit=limit)
    #     ni.update_configurations()
    #     if not check and not apply:
    #         sys.exit(0)

    # ni.init(limit=limit)

    # ni.import_devices_from_configs()
    # ni.import_devices_from_cmds()

    # ni.import_cabling()

    # ni.check_data_consistency()

    # # ------------------------------------------------------------------------------------
    # # Update Remote if apply is enabled
    # # ------------------------------------------------------------------------------------
    if apply:
        nb.sync(ni)

    elif check:
        diff = nb.diff(ni)
        diff.print_detailed()
    # if config.logs["performance_log"]:
    #     perf.TIME_TRACKER.set_nbr_devices(len(ni.devs.inventory.hosts.keys()))
    #     perf.TIME_TRACKER.print_all()

    # if config.netbox["status_update"] and apply:
    #     ni.update_devices_status()

    # if diff:
    #     ni.print_diffs()

    # logger.info(
    #     f"Execution finished, processed {perf.TIME_TRACKER.nbr_devices} device(s) "
    # )
    if debug:
        pdb.set_trace()


if __name__ == "__main__":
    main()
