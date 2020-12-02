"""Tasks for use with Invoke."""
import os
import sys
import time
from invoke import task

try:
    import toml
except ImportError:
    sys.exit("Please make sure to `pip install toml` or enable the Poetry shell and run `poetry install`.")


def project_ver():
    """Find version from pyproject.toml to use for docker image tagging."""
    with open("pyproject.toml") as file:
        return toml.load(file)["tool"]["poetry"].get("version", "latest")


# Can be set to a separate Python version to be used for launching or building image
PYTHON_VER = os.getenv("PYTHON_VER", "3.7")
# Name of the docker image/image
NAME = os.getenv("IMAGE_NAME", f"network-importer-py{PYTHON_VER}")
# Tag for the image
IMAGE_VER = os.getenv("IMAGE_VER", project_ver())
# Gather current working directory for Docker commands
PWD = os.getcwd()
# Local or Docker execution provide "local" to run locally without docker execution
INVOKE_LOCAL = os.getenv("INVOKE_LOCAL", False)  # pylint: disable=W1508

# Environment Variables for Travis-CI
TRAVIS_NETBOX_ADDRESS = "http://localhost:8000"
TRAVIS_NETBOX_TOKEN = "0123456789abcdef0123456789abcdef01234567"
TRAVIS_NETBOX_VERIFY_SSL = "false"
TRAVIS_BATFISH_ADDRESS = "localhost"
TRAVIS_ANSIBLE_PYTHON_INTERPRETER = "$(which python)"
TRAVIS_EXAMPLES = ["spine_leaf_01", "multi_site_02"]
TRAVIS_BATFISH_VERSION = "2020.10.08.667"


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
    if local:
        print(f"LOCAL - Running command {exec_cmd}")
        result = context.run(exec_cmd, pty=True)
    else:
        print(f"DOCKER - Running command: {exec_cmd} container: {name}:{image_ver}")
        result = context.run(f"docker run -it -v {PWD}:/local {name}:{image_ver} {exec_cmd}", pty=True)

    return result


@task
def build_image(context, name=NAME, python_ver=PYTHON_VER, image_ver=IMAGE_VER):
    """This will build an image with the provided name and python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Define the Python version docker image to build from
        image_ver (str): Define image version
    """
    print(f"Building image {name}:{image_ver}")
    result = context.run(f"docker build --tag {name}:{image_ver} --build-arg PYTHON_VER={python_ver} -f Dockerfile .",)
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
    if not local:
        exec_cmd = "sh -c 'find . -name " "*.py" " | xargs pylint'"  # pylint: disable=W1404
    else:
        exec_cmd = "find . -name '*.py' | xargs pylint"
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
    exec_cmd = "yamllint ."
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


def compose_netbox(context):
    """Create Netbox instance for Travis testing."""
    context.run("cd /tmp", pty=True)
    context.run("git clone -b release https://github.com/netbox-community/netbox-docker.git", pty=True)
    context.run("cd netbox-docker", pty=True)
    context.run(
        """tee docker-compose.override.yml <<EOF
version: '3.4'
services:
    nginx:
        ports:
        - 8000:8080
EOF""",
        pty=True,
    )
    context.run("docker-compose pull", pty=True)
    context.run("docker-compose up -d", pty=True)


def compose_batfish(context):
    """Create Batfish instance for Travis testing."""
    exec_cmd = f"docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish:{TRAVIS_BATFISH_VERSION}"
    context.run(exec_cmd, pty=True)


def configure_netbox(context, example_name):
    """Configure Netbox instance with Ansible."""
    context.run(f"cd {PWD}/examples/{example_name}", pty=True)
    context.run("ansible-playbook pb.netbox_setup.yaml", pty=True)


def run_network_importer(context, example_name):
    """Run Network Importer."""
    context.run(f"cd {PWD}/examples/{example_name}", pty=True)
    context.run("network-importer --apply", pty=True)


@task
def integration_tests(context):
    """Builds test environment for Travis-CI."""
    os.environ["NETBOX_ADDRESS"] = TRAVIS_NETBOX_ADDRESS
    os.environ["NETBOX_TOKEN"] = TRAVIS_NETBOX_TOKEN
    os.environ["NETBOX_VERIFY_SSL"] = TRAVIS_NETBOX_VERIFY_SSL
    os.environ["BATFISH_ADDRESS"] = TRAVIS_BATFISH_ADDRESS
    os.environ["ANSIBLE_PYTHON_INTERPRETER"] = TRAVIS_ANSIBLE_PYTHON_INTERPRETER
    compose_netbox(context)
    tests(context)
    compose_batfish(context)
    time.sleep(90)
    for example in TRAVIS_EXAMPLES:
        configure_netbox(context, example)
        run_network_importer(context, example)
    print("All integration tests have passed!")


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
