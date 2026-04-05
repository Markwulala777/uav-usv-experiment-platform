from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    scenario_config = LaunchConfiguration("scenario_config")
    output_root = LaunchConfiguration("output_root")
    run_id = LaunchConfiguration("run_id")
    seed = LaunchConfiguration("seed")
    scenario_id = LaunchConfiguration("scenario_id")
    mode = LaunchConfiguration("mode")
    reference_source = LaunchConfiguration("reference_source")

    config_path = PathJoinSubstitution([FindPackageShare("joint_bringup"), "config", scenario_config])

    return LaunchDescription(
        [
            DeclareLaunchArgument("scenario_config", default_value="calm_truth.yaml"),
            DeclareLaunchArgument("output_root", default_value="~/uav-usv-experiment-runs"),
            DeclareLaunchArgument("run_id", default_value=""),
            DeclareLaunchArgument("seed", default_value="42"),
            DeclareLaunchArgument("scenario_id", default_value="calm_truth"),
            DeclareLaunchArgument("mode", default_value="baseline_minimal"),
            DeclareLaunchArgument("reference_source", default_value="guidance"),
            SetParameter(name="use_sim_time", value=True),
            Node(
                package="experiment_manager",
                executable="scenario_runner",
                name="experiment_manager",
                output="screen",
                parameters=[
                    config_path,
                    {
                        "output_root": output_root,
                        "run_id": run_id,
                        "seed": seed,
                        "scenario_id": scenario_id,
                        "mode": mode,
                    },
                ],
            ),
            Node(
                package="platform_interface",
                executable="platform_truth_ingest",
                name="platform_truth_ingest",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="platform_interface",
                executable="platform_landing_zone_state",
                name="platform_landing_zone_state",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="platform_interface",
                executable="platform_uav_truth_provider",
                name="platform_uav_truth_provider",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="relative_estimation",
                executable="truth_relative_state",
                name="relative_estimation_truth",
                output="screen",
            ),
            Node(
                package="relative_estimation",
                executable="active_state_mux",
                name="relative_state_active_mux",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="mission_manager",
                executable="phase_manager",
                name="mission_manager",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="landing_decision",
                executable="window_status",
                name="window_status",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="landing_decision",
                executable="decision_advisory",
                name="decision_advisory",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="landing_guidance",
                executable="stage_reference",
                name="landing_guidance",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="trajectory_planner",
                executable="moving_deck_planner",
                name="trajectory_planner",
                output="screen",
            ),
            Node(
                package="safety_manager",
                executable="safety_monitor",
                name="safety_manager",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="controller_interface",
                executable="reference_mux",
                name="reference_mux",
                output="screen",
                parameters=[config_path, {"source_mode": reference_source}],
            ),
            Node(
                package="safety_manager",
                executable="reference_filter",
                name="reference_filter",
                output="screen",
            ),
            Node(
                package="controller_interface",
                executable="tracking_controller",
                name="tracking_controller",
                output="screen",
            ),
            Node(
                package="controller_interface",
                executable="px4_offboard_bridge",
                name="px4_offboard_bridge",
                output="screen",
            ),
            Node(
                package="touchdown_manager",
                executable="contact_monitor",
                name="touchdown_manager",
                output="screen",
                parameters=[config_path],
            ),
            Node(
                package="metrics_evaluator",
                executable="summary_writer",
                name="metrics_evaluator",
                output="screen",
            ),
            Node(
                package="metrics_evaluator",
                executable="frame_audit",
                name="frame_audit",
                output="screen",
            ),
        ]
    )
