# joint_bringup

Launch-only package for the ROS 2 research layer.

`mission_stack_full.launch.py` composes the shared task chain, while the
scenario-specific launch files set the default scene/profile combinations.

Primary entry points:

- `mission_stack_minimal.launch.py`
- `mission_stack_full.launch.py`
- `scenario_1_static_ground_qr.launch.py`
- `scenario_2_ground_moving_qr.launch.py`
- `scenario_3_maritime_usv_qr.launch.py`

The formal scenario 1/2/3 chain-validation entrypoint stays one level above bringup in
`scripts/run_chain_validation.sh`, which wraps ROS 1 world startup,
`platform_interface_ros1`, `ros1_bridge`, ROS 2 bringup, and the scenario-2
UGV motion baseline into a single repeatable validation command. It is not the
general day-to-day mission runtime entrypoint.

ROS 1 world selection is now centralized in `scripts/run_ros1_world.sh --scenario ...`.
Scenario-specific ROS 2 launch files do not own world selection.

Common launch overrides:

- `planner_backend`
- `reference_source`
- `enable_planner`
- `enable_decision`
- `enable_safety`
- `enable_touchdown`

Compatibility launch files such as `baseline_minimal.launch.py` remain
available for older workflows, but new work should prefer the mission-stack and
scenario-prefixed entry points.

Scenario defaults frozen for chain validation:

- `scenario_1_static_ground_qr`
  Uses `run_ros1_world.sh --scenario scenario_1_static_ground_qr`, which resolves
  to `zhihang1.launch`, plus canonical target `landing1` and zero
  platform/landing-zone offsets.
- `scenario_2_ground_moving_qr`
  Uses `run_ros1_world.sh --scenario scenario_2_ground_moving_qr`, which
  resolves to `outdoor2_precision_landing.launch`, plus canonical platform `ugv_0`, a
  static `iris_0` truth carrier in Gazebo, and a 10 Hz low-speed
  `/ugv_0/cmd_vel` baseline. The validated runtime now includes the ROS 1
  controller packages needed for pure `catvehicle` motion, while Gazebo
  model-state fallback remains available only as a guarded backup path.
- `scenario_3_maritime_usv_qr`
  Uses `run_ros1_world.sh --scenario scenario_3_maritime_usv_qr`, which
  resolves to `sandisland.launch` with `example_course.world`, plus canonical
  platform `wamv` in `maritime_usv` mode,
  `platform_offset_xyz=[0.0, 0.0, 1.25]`, and
  `landing_zone_offset_xyz=[0.5, 0.0, 1.25]`.
