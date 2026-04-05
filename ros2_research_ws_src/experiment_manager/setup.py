from setuptools import setup

package_name = "experiment_manager"

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
        (
            "share/" + package_name + "/config",
            [
                "config/scenario_1_static_ground_qr.yaml",
                "config/scenario_2_ground_moving_qr.yaml",
                "config/scenario_3_maritime_usv_qr.yaml",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="jia",
    maintainer_email="jia@example.com",
    description="Run-context publication and event logging for research experiments.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "scenario_runner = experiment_manager.scenario_runner:main",
        ],
    },
)
