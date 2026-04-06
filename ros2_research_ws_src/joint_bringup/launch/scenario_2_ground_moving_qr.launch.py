from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    output_root = LaunchConfiguration("output_root")
    run_id = LaunchConfiguration("run_id")
    return LaunchDescription(
        [
            DeclareLaunchArgument("output_root", default_value="~/uav-landing-experiment-runs"),
            DeclareLaunchArgument("run_id", default_value=""),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("joint_bringup"), "launch", "mission_stack_full.launch.py"]
                    )
                ),
                launch_arguments={
                    "scenario_config": "scenario_2_ground_moving_qr.yaml",
                    "planner_config": "planner_moving_target.yaml",
                    "planner_backend": "scenario_default",
                    "reference_source": "scenario_default",
                    "output_root": output_root,
                    "run_id": run_id,
                    "enable_planner": "true",
                    "enable_decision": "true",
                    "enable_window_logic": "false",
                    "enable_safety": "true",
                    "enable_touchdown": "true",
                }.items(),
            )
        ]
    )
