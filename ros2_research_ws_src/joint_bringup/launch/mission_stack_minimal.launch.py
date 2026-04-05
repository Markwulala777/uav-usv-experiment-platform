from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("joint_bringup"), "launch", "mission_stack_full.launch.py"]
                    )
                ),
                launch_arguments={
                    "scenario_config": "scenario_1_static_ground_qr.yaml",
                    "planner_config": "planner_baseline.yaml",
                    "planner_backend": "scenario_default",
                    "reference_source": "scenario_default",
                    "enable_planner": "true",
                    "enable_decision": "false",
                    "enable_window_logic": "false",
                    "enable_safety": "true",
                    "enable_touchdown": "true",
                }.items(),
            )
        ]
    )
