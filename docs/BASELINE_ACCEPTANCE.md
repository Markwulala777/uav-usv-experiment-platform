# Baseline Acceptance Checklist

This checklist is intended to validate the shared-world truth-level landing baseline, not the full doctoral platform.

## Required acceptance items

- One shared Gazebo world only
- ROS2 research nodes run with `use_sim_time=true`
- Truth platform/deck and relative-state interfaces are available
- The frame convention is frozen and the ENU-to-NED conversion happens exactly once in `controller_interface/px4_offboard_bridge`
- Frame audit passes with configured tolerances
- `landing_guidance` owns geometric reference generation, while `controller_interface` owns the only PX4 offboard output path
- Pre-touchdown corridor hold is measurable
- Touchdown outcomes are labeled
- Per-run metadata and summary metrics are written to disk
- Calm and moderate scenarios are both representable through configuration

## Baseline deliverables in this repository

- `platform_interface_ros1`
- `mission_stack_msgs`
- `platform_interface`
- `relative_estimation`
- `mission_manager`
- `landing_decision`
- `landing_guidance`
- `trajectory_planner`
- `safety_manager`
- `controller_interface`
- `touchdown_manager`
- `experiment_manager`
- `metrics_evaluator`
- `joint_bringup`
