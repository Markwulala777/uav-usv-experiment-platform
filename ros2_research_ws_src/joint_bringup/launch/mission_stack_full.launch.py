from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    scenario_config = LaunchConfiguration("scenario_config")
    planner_config = LaunchConfiguration("planner_config")
    output_root = LaunchConfiguration("output_root")
    run_id = LaunchConfiguration("run_id")
    seed = LaunchConfiguration("seed")
    planner_backend = LaunchConfiguration("planner_backend")
    reference_source = LaunchConfiguration("reference_source")
    enable_planner = LaunchConfiguration("enable_planner")
    enable_decision = LaunchConfiguration("enable_decision")
    enable_window_logic = LaunchConfiguration("enable_window_logic")
    enable_safety = LaunchConfiguration("enable_safety")
    enable_touchdown = LaunchConfiguration("enable_touchdown")

    scenario_config_path = PathJoinSubstitution(
        [FindPackageShare("experiment_manager"), "config", scenario_config]
    )
    planner_config_path = PathJoinSubstitution(
        [FindPackageShare("trajectory_planner"), "config", planner_config]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "scenario_config", default_value="scenario_1_static_ground_qr.yaml"
            ),
            DeclareLaunchArgument("planner_config", default_value="planner_baseline.yaml"),
            DeclareLaunchArgument("output_root", default_value="~/uav-landing-experiment-runs"),
            DeclareLaunchArgument("run_id", default_value=""),
            DeclareLaunchArgument("seed", default_value="42"),
            DeclareLaunchArgument("planner_backend", default_value="scenario_default"),
            DeclareLaunchArgument("reference_source", default_value="scenario_default"),
            DeclareLaunchArgument("enable_planner", default_value="true"),
            DeclareLaunchArgument("enable_decision", default_value="false"),
            DeclareLaunchArgument("enable_window_logic", default_value="false"),
            DeclareLaunchArgument("enable_safety", default_value="true"),
            DeclareLaunchArgument("enable_touchdown", default_value="true"),
            SetParameter(name="use_sim_time", value=True),
            Node(
                package="experiment_manager",
                executable="scenario_runner",
                name="experiment_manager",
                output="screen",
                parameters=[
                    scenario_config_path,
                    {
                        "output_root": output_root,
                        "run_id": run_id,
                        "seed": seed,
                    },
                ],
            ),
            Node(
                package="platform_interface",
                executable="platform_truth_ingest",
                name="platform_truth_ingest",
                output="screen",
                parameters=[scenario_config_path],
            ),
            Node(
                package="platform_interface",
                executable="platform_landing_zone_state",
                name="platform_landing_zone_state",
                output="screen",
                parameters=[scenario_config_path],
            ),
            Node(
                package="platform_interface",
                executable="platform_uav_truth_provider",
                name="platform_uav_truth_provider",
                output="screen",
                parameters=[scenario_config_path],
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
                parameters=[scenario_config_path],
            ),
            Node(
                package="mission_manager",
                executable="phase_manager",
                name="mission_manager",
                output="screen",
                parameters=[scenario_config_path],
            ),
            Node(
                package="landing_decision",
                executable="window_status",
                name="window_status",
                output="screen",
                parameters=[scenario_config_path],
                condition=IfCondition(enable_window_logic),
            ),
            Node(
                package="landing_decision",
                executable="decision_advisory",
                name="decision_advisory",
                output="screen",
                parameters=[scenario_config_path],
                condition=IfCondition(enable_decision),
            ),
            Node(
                package="landing_guidance",
                executable="stage_reference",
                name="landing_guidance",
                output="screen",
                parameters=[scenario_config_path],
            ),
            Node(
                package="trajectory_planner",
                executable="trajectory_planner_node",
                name="trajectory_planner",
                output="screen",
                parameters=[
                    scenario_config_path,
                    planner_config_path,
                    {"planner_backend": planner_backend},
                ],
                condition=IfCondition(enable_planner),
            ),
            Node(
                package="safety_manager",
                executable="safety_monitor",
                name="safety_manager",
                output="screen",
                parameters=[scenario_config_path],
                condition=IfCondition(enable_safety),
            ),
            Node(
                package="controller_interface",
                executable="reference_mux",
                name="reference_mux",
                output="screen",
                parameters=[scenario_config_path, {"reference_source": reference_source}],
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
                parameters=[scenario_config_path],
                condition=IfCondition(enable_touchdown),
            ),
            Node(
                package="metrics_evaluator",
                executable="summary_writer",
                name="metrics_evaluator",
                output="screen",
                parameters=[scenario_config_path],
            ),
            Node(
                package="metrics_evaluator",
                executable="frame_audit",
                name="frame_audit",
                output="screen",
                parameters=[scenario_config_path],
            ),
            Node(
                package="metrics_evaluator",
                executable="geometry_consistency",
                name="geometry_consistency",
                output="screen",
                parameters=[scenario_config_path],
            ),
        ]
    )
