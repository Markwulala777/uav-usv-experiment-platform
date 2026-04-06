from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    scenario_config = LaunchConfiguration("scenario_config")
    output_root = LaunchConfiguration("output_root")
    run_id = LaunchConfiguration("run_id")
    seed = LaunchConfiguration("seed")
    scenario_id = LaunchConfiguration("scenario_id")
    mode = LaunchConfiguration("mode")
    reference_source = LaunchConfiguration("reference_source")

    return LaunchDescription(
        [
            DeclareLaunchArgument("scenario_config", default_value="calm_truth.yaml"),
            DeclareLaunchArgument("output_root", default_value="~/uav-landing-experiment-runs"),
            DeclareLaunchArgument("run_id", default_value=""),
            DeclareLaunchArgument("seed", default_value="42"),
            DeclareLaunchArgument("scenario_id", default_value="calm_truth"),
            DeclareLaunchArgument("mode", default_value="baseline_minimal"),
            DeclareLaunchArgument("reference_source", default_value="guidance"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([FindPackageShare("joint_bringup"), "launch", "baseline_minimal.launch.py"])
                ),
                launch_arguments={
                    "scenario_config": scenario_config,
                    "output_root": output_root,
                    "run_id": run_id,
                    "seed": seed,
                    "scenario_id": scenario_id,
                    "mode": mode,
                    "reference_source": reference_source,
                }.items(),
            )
        ]
    )
