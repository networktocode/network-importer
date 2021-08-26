"""Tasks for use with Invoke."""
import time
import os
import sys
from distutils.util import strtobool
from invoke import task

try:
    import toml
except ImportError:
    sys.exit("Please make sure to `pip install toml` or enable the Poetry shell and run `poetry install`.")

NETBOX_VERSIONS = {
    "v2.10": {"netbox_version": "v2.10.2", "docker_version": "0.27.0"},
    "v2.9": {"netbox_version": "v2.9.11", "docker_version": "0.26.2"},
    "v2.8": {"netbox_version": "v2.8.9", "docker_version": "0.24.1"},
}

NAUTOBOT_VER = "v1.0.1"


def project_ver():
    """Find version from pyproject.toml to use for docker image tagging."""
    with open("pyproject.toml") as file:
        return toml.load(file)["tool"]["poetry"].get("version", "latest")


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg
    return bool(strtobool(arg))


# Can be set to a separate Python version to be used for launching or building image
PYTHON_VER = os.getenv("PYTHON_VER", os.getenv("TRAVIS_PYTHON_VERSION", "3.7"))
# Name of the docker image/image
NAME = os.getenv("IMAGE_NAME", f"network-importer-py{PYTHON_VER}")
# Tag for the image
IMAGE_VER = os.getenv("IMAGE_VER", project_ver())
# Gather current working directory for Docker commands
PWD = os.getcwd()
# Local or Docker execution provide "local" to run locally without docker execution
INVOKE_LOCAL = is_truthy(os.getenv("INVOKE_LOCAL", False))  # pylint: disable=W1508

# Environment Variables for Travis-CI
NETBOX_VERSION = os.getenv("NETBOX_VERSION", "v2.9")
TRAVIS_NETBOX_ADDRESS = "http://localhost:8000"
TRAVIS_NETBOX_TOKEN = "0123456789abcdef0123456789abcdef01234567"  # nosec - bandit ignore possible password
TRAVIS_NETBOX_VERIFY_SSL = "false"
TRAVIS_BATFISH_ADDRESS = "localhost"
TRAVIS_ANSIBLE_PYTHON_INTERPRETER = "$(which python)"
TRAVIS_EXAMPLES = ["spine_leaf_01", "multi_site_02"]
TRAVIS_BATFISH_VERSION = "2020.10.08.667"
TRAVIS_NAUTOBOT_ADDRESS = "http://localhost:8000"
TRAVIS_NAUTOBOT_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # nosec - bandit ignore possible password
TRAVIS_NAUTOBOT_VERIFY_SSL = "false"
NAUTOBOT_VERSION = os.getenv("NAUTOBOT_VERSION", "v1.0.1")


def run_cmd(context, exec_cmd, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """Wrapper to run the invoke task commands.

    Args:
        context ([invoke.task]): Invoke task object.
        exec_cmd ([str]): Command to run.
        name ([str], optional): Image name to use if exec_env is `docker`. Defaults to NAME.
        image_ver ([str], optional): Version of image to use if exec_env is `docker`. Defaults to IMAGE_VER.
        local (bool): Define as `True` to execute locally

    Returns:
        result (obj): Contains Invoke result from running task.
    """
    if is_truthy(local):
        print(f"LOCAL - Running command {exec_cmd}")
        result = context.run(exec_cmd, pty=True)
    else:
        print(f"DOCKER - Running command: {exec_cmd} container: {name}:{image_ver}")
        result = context.run(f"docker run -it -v {PWD}:/local {name}:{image_ver} sh -c '{exec_cmd}'", pty=True)

    return result


@task
def build_image(
    context, name=NAME, python_ver=PYTHON_VER, image_ver=IMAGE_VER, nocache=False, forcerm=False
):  # pylint: disable=too-many-arguments
    """This will build an image with the provided name and python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Define the Python version docker image to build from
        image_ver (str): Define image version
        nocache (bool): Do not use cache when building the image
        forcerm (bool): Always remove intermediate containers
    """
    print(f"Building image {name}:{image_ver}")
    command = f"docker build --tag {name}:{image_ver} --build-arg PYTHON_VER={python_ver} -f Dockerfile ."

    if nocache:
        command += " --no-cache"
    if forcerm:
        command += " --force-rm"

    result = context.run(command, hide=False)
    if result.exited != 0:
        print(f"Failed to build image {name}:{image_ver}\nError: {result.stderr}")


@task
def clean_image(context, name=NAME, image_ver=IMAGE_VER):
    """This will remove the specific image.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
    """
    print(f"Attempting to forcefully remove image {name}:{image_ver}")
    context.run(f"docker rmi {name}:{image_ver} --force")
    print(f"Successfully removed image {name}:{image_ver}")


@task
def rebuild_image(context, name=NAME, python_ver=PYTHON_VER, image_ver=IMAGE_VER):
    """This will clean the image and then rebuild image without using cache.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Define the Python version docker image to build from
        image_ver (str): Define image version
    """
    clean_image(context, name, image_ver)
    build_image(context, name, python_ver, image_ver)


@task
def pytest(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run pytest for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Will use the container version docker image
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    # Install python module
    exec_cmd = "pytest -vv"
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def black(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run black to check that Python files adherence to black standards.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "black --check --diff ."
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def flake8(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run flake8 for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "flake8 ."
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def pylint(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run pylint for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = 'find . -name "*.py" | xargs pylint'
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def yamllint(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run yamllint to validate formatting adheres to NTC defined YAML standards.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "yamllint . --format github"
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def pydocstyle(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run pydocstyle to validate docstring formatting adheres to NTC defined standards.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "pydocstyle ."
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def bandit(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run bandit to validate basic static code security analysis.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "bandit --recursive ./ --configfile .bandit.yml"
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def cli(context, name=NAME, image_ver=IMAGE_VER):
    """This will enter the image to perform troubleshooting or dev work.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
    """
    dev = f"docker run -it -v {PWD}:/local {name}:{image_ver} /bin/bash"
    context.run(f"{dev}", pty=True)


def compose_netbox(
    context, var_envs, netbox_docker_ver="release",
):
    """Create Netbox instance for Travis testing.

    Args:
        context (obj): Used to run specific commands
        var_envs (dict): Environment variables to pass to the command runner
        netbox_docker_ver (str): Version of Netbox docker to use
    """
    context.run(
        f"cd /tmp && git clone -b {netbox_docker_ver} https://github.com/netbox-community/netbox-docker.git",
        pty=True,
        env=var_envs,
    )
    context.run(
        """cd /tmp/netbox-docker && tee docker-compose.override.yml <<EOF
version: '3.4'
services:
  nginx:
    ports:
      - 8000:8080
EOF""",
        pty=True,
        env=var_envs,
    )
    context.run("cd /tmp/netbox-docker && docker-compose pull", pty=True, env=var_envs)
    context.run("cd /tmp/netbox-docker && docker-compose up -d", pty=True, env=var_envs)


def compose_batfish(context, var_envs):
    """Create Batfish instance for Travis testing.

    Args:
        context (obj): Used to run specific commands
        var_envs (dict): Environment variables to pass to the command runner
    """
    exec_cmd = f"docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish:{TRAVIS_BATFISH_VERSION}"
    context.run(exec_cmd, pty=True, env=var_envs)


def configure_netbox(context, example_name, var_envs):
    """Configure Netbox instance with Ansible.

    Args:
        context (obj): Used to run specific commands
        example_name (str): Name of the example directory to use
        var_envs (dict): Environment variables to pass to the command runner
    """
    context.run(f"cd {PWD}/examples/{example_name} && ansible-playbook pb.netbox_setup.yaml", pty=True, env=var_envs)


def run_network_importer(context, example_name, var_envs, config_file="network_importer.toml"):
    """Run Network Importer.

    Args:
        context (obj): Used to run specific commands
        example_name (str): Name of the example directory to use
        var_envs (dict): Environment variables to pass to the command runner
        config_file (str): Name of the configuration file. Optional, defaults to `network_importer.toml`
    """
    context.run(
        f"cd {PWD}/examples/{example_name} && network-importer check  --config {config_file}", pty=True, env=var_envs
    )
    context.run(
        f"cd {PWD}/examples/{example_name} && network-importer apply --config {config_file}", pty=True, env=var_envs
    )
    output_last_check = context.run(
        f"cd {PWD}/examples/{example_name} && network-importer check --config {config_file}", pty=True, env=var_envs
    )

    if "no diffs" not in output_last_check.stdout:
        print("'network-importer check' didn't return 'no diffs' after 'network-importer apply'")
        sys.exit(1)


@task
def integration_tests(context, netbox_ver=NETBOX_VERSION):
    """Builds test environment for Travis-CI.

    Args:
        context (obj): Used to run specific commands
        netbox_ver (str): Major Netbox version to use for testing
    """
    docker_netbox_version = NETBOX_VERSIONS.get(netbox_ver, {}).get("docker_version", "release")
    netbox_exact_version = NETBOX_VERSIONS.get(netbox_ver, {}).get("netbox_version", "latest")

    envs = {
        "VERSION": netbox_exact_version,
        "NETBOX_ADDRESS": TRAVIS_NETBOX_ADDRESS,
        "NETBOX_TOKEN": TRAVIS_NETBOX_TOKEN,
        "NETBOX_VERIFY_SSL": TRAVIS_NETBOX_VERIFY_SSL,
        "BATFISH_ADDRESS": TRAVIS_BATFISH_ADDRESS,
        "ANSIBLE_PYTHON_INTERPRETER": TRAVIS_ANSIBLE_PYTHON_INTERPRETER,
    }

    compose_netbox(context, netbox_docker_ver=docker_netbox_version, var_envs=envs)
    compose_batfish(context, var_envs=envs)
    time.sleep(90)
    for example in TRAVIS_EXAMPLES:
        configure_netbox(context, example, var_envs=envs)
        run_network_importer(context, example, var_envs=envs)
    print(
        f"All integration tests have passed for Netbox {netbox_exact_version} / Netbox Docker {docker_netbox_version}!"
    )


def compose_nautobot(context):
    """Create Netbox instance for Travis testing.

    Args:
        context (obj): Used to run specific commands
        var_envs (dict): Environment variables to pass to the command runner
        netbox_docker_ver (str): Version of Netbox docker to use
    """
    # Copy the file from tests/docker-compose.test.yml to the tmp directory to be executed from there
    # context.run(
    #     f"cp {PWD}/tests/nautobot-docker-compose.test.yml /tmp/docker-compose.yml", pty=True, env=var_envs,
    # )
    # context.run(
    #     f"cp {PWD}/tests/nginx.conf /tmp/nginx.conf", pty=True, env=var_envs,
    # )
    # context.run(
    #     f"cp {PWD}/tests/.creds.env.test /tmp/.creds.tests.env", pty=True, env=var_envs,
    # )
    # context.run("cd /tmp && docker-compose pull", pty=True, env=var_envs)
    # context.run("cd /tmp && docker-compose down", pty=True, env=var_envs)
    # context.run("cd /tmp && docker-compose up -d", pty=True, env=var_envs)

    # Clone the repo so the latest data is present
    context.run("docker pull networktocode/nautobot-lab:latest ", pty=True)

    # Start the container
    context.run(
        "docker run -itd --rm --name nautobot -v $(pwd)/uwsgi.ini:/opt/nautobot/uwsgi.ini -p 8000:8000 networktocode/nautobot-lab:latest",
        pty=True,
    )

    # Execute the load demo data
    context.run("sleep 5 && docker exec -it nautobot load-mock-data", pty=True)

    # Print out the ports listening to verify it is running
    context.run("ss -ltn", pty=True)


def configure_nautobot(context, example_name, var_envs):
    """Configure Netbox instance with Ansible.

    Args:
        context (obj): Used to run specific commands
        example_name (str): Name of the example directory to use
        var_envs (dict): Environment variables to pass to the command runner
    """
    # Sleep for a minute to allow all systems to be up and running
    # context.run("sleep 60", pty=True, env=var_envs)
    # context.run(f"cd {PWD}/examples/{example_name} && python3 nautobot_setup.py", pty=True, env=var_envs)
    context.run(
        f"cd {PWD}/examples/{example_name} && ansible-playbook pb.nautobot_setup.yaml -vv ", pty=True, env=var_envs
    )


@task
def nautobot_integration_tests(context, nautobot_ver=NAUTOBOT_VER):
    """Builds Nautobot test environment for Travis-CI.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use for testing
    """
    envs = {
        "VERSION": nautobot_ver,
        "NAUTOBOT_ADDRESS": TRAVIS_NAUTOBOT_ADDRESS,
        "NAUTOBOT_TOKEN": TRAVIS_NAUTOBOT_TOKEN,
        "NAUTOBOT_VERIFY_SSL": TRAVIS_NAUTOBOT_VERIFY_SSL,
        "BATFISH_ADDRESS": TRAVIS_BATFISH_ADDRESS,
        "ANSIBLE_PYTHON_INTERPRETER": TRAVIS_ANSIBLE_PYTHON_INTERPRETER,
    }

    compose_nautobot(context)
    compose_batfish(context, var_envs=envs)
    time.sleep(45)
    for example in TRAVIS_EXAMPLES:
        configure_nautobot(context, example, var_envs=envs)
        run_network_importer(context, example, var_envs=envs, config_file="network_importer_nautobot.toml")
    print(f"All integration tests have passed for Nautobot {nautobot_ver}")


@task
def tests(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run all tests for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    black(context, name, image_ver, local)
    flake8(context, name, image_ver, local)
    pylint(context, name, image_ver, local)
    yamllint(context, name, image_ver, local)
    pydocstyle(context, name, image_ver, local)
    bandit(context, name, image_ver, local)
    pytest(context, name, image_ver, local)

    print("All tests have passed!")
