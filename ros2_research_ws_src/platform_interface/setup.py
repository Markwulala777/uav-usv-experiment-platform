from setuptools import find_packages, setup

package_name = "platform_interface"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="jia",
    maintainer_email="jia@example.com",
    description="ROS 2 relay for bridged truth topics.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "platform_truth_ingest = platform_interface.platform_truth_ingest_node:main",
            "platform_landing_zone_state = platform_interface.platform_landing_zone_state_node:main",
            "platform_uav_truth_provider = platform_interface.transitional.platform_uav_truth_provider_node:main",
            "platform_truth_relay = platform_interface.platform_truth_ingest_node:main",
        ],
    },
)
