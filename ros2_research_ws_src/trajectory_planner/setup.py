from setuptools import setup

package_name = "trajectory_planner"

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
                "config/planner_baseline.yaml",
                "config/planner_moving_target.yaml",
                "config/planner_chance_constrained.yaml",
                "config/planner_tube_based.yaml",
                "config/planner_learning_augmented.yaml",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="jia",
    maintainer_email="jia@example.com",
    description="Trajectory planning interfaces and stubs.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "moving_deck_planner = trajectory_planner.moving_deck_planner_node:main",
            "trajectory_planner_node = trajectory_planner.moving_deck_planner_node:main",
        ],
    },
)
