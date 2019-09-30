from setuptools import setup, find_packages

package_version = "0.1.0"
package_name = "network-importer"


def requirements(filename="requirements.txt"):
    return open(filename.strip()).readlines()


with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name=package_name,
    version=package_version,
    description="Network Importer tool to import an existing network into a Database /Source Of Truth",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Damien Garros",
    packages=find_packages(),
    install_requires=requirements(),
    include_package_data=True,
    scripts=["bin/network-importer"],
)
