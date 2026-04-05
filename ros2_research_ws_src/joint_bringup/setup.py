from setuptools import setup

package_name = "joint_bringup"

setup(
    name=package_name,
    version="0.0.1",
    packages=[],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
        ("share/" + package_name + "/config", ["config/calm_truth.yaml", "config/moderate_truth.yaml"]),
        (
            "share/" + package_name + "/launch",
            [
                "launch/baseline_minimal.launch.py",
                "launch/controller_integration.launch.py",
                "launch/full_landing_mission.launch.py",
                "launch/mission_stack_full.launch.py",
                "launch/mission_stack_minimal.launch.py",
                "launch/phase_b_minimal.launch.py",
                "launch/planner_test.launch.py",
                "launch/scenario_1_static_ground_qr.launch.py",
                "launch/scenario_2_ground_moving_qr.launch.py",
                "launch/scenario_3_maritime_usv_qr.launch.py",
                "launch/stage1_joint.launch.py",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="jia",
    maintainer_email="jia@example.com",
    description="Launch entry points for the mixed UAV-USV stack.",
    license="MIT",
)
