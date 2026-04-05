# Mixed ROS1/ROS2 Architecture

This repository now carries the current research baseline for the stricter mixed ROS1/ROS2 research-platform architecture:

- ROS 1 / catkin remains the environment carrier:
  - VRX Classic assets
  - Gazebo Classic shared world
  - WAM-V / maritime disturbance base
  - truth extraction from `/gazebo/model_states`
- ROS 2 / colcon becomes the research layer:
  - shared research-layer interface contracts
  - platform interface normalization
  - relative-state estimation
  - mission-phase ownership
  - landing-window and advisory logic
  - trajectory/reference selection
  - safety monitoring
  - touchdown monitoring
  - landing-guidance logic
- PX4 remains the flight-control carrier.
- Micro XRCE-DDS remains the PX4-to-ROS 2 transport path.
- `ros1_bridge` is the ROS 1 <-> ROS 2 exchange layer and is built from source inside the runtime.

## Layer boundaries

### ROS 1 side

`platform_interface_ros1` is the first strict interface node on the ROS 1 side.
It converts the broad Gazebo truth feed into a smaller contract:

- `/bridge/deck/truth/pose`
- `/bridge/deck/truth/twist`
- `/bridge/landing_target/truth/pose`
- `/bridge/landing_target/truth/twist`
- `/bridge/uav/truth/pose`
- `/bridge/uav/truth/twist`
- `/bridge/relative/truth/pose`
- `/bridge/relative/truth/twist`

These topics are intentionally standard-message-only so they can cross `ros1_bridge` without introducing a custom message build in both middleware stacks.

### ROS 2 side

The ROS 2 research workspace is organized under `ros2_research_ws_src/` and currently starts the first research modules:

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

## Frozen coordinate ownership

The current baseline uses a strict frame boundary between the research layer and PX4:

- ROS 1 truth extraction stays in Gazebo `world` ENU.
- ROS 2 research nodes consume truth and publish guidance in `world` ENU.
- `controller_interface/px4_offboard_bridge` is the only place where research-layer commands cross into PX4 local coordinates.
- The bridge performs one conversion chain only:
  - `world ENU -> local ENU -> local NED`
- The bridge resolves the PX4 local origin from truth UAV pose plus PX4 local-position feedback.
- If PX4 local position resets, the bridge keeps the OFFBOARD heartbeat alive and holds the last valid local NED setpoint until the local origin is resolved again.

This keeps the research-layer API independent of PX4 coordinate conventions and prevents duplicate ENU-to-NED conversions in upstream nodes.

The current baseline now includes:

- truth-level landing-zone publication inside `platform_interface`
- ROS2-to-PX4 offboard bridge output
- frame-audit reporting via `metrics_evaluator`
- per-run metadata generation
- summary metric extraction

The major remaining gap before thesis-grade comparative studies is not package presence, but richer experiment coverage:

- delay and noise injection
- perception-only relative estimation
- stronger touchdown/contact realism
- batch comparison protocols across controller variants

## Bring-up order

1. Build the ROS 1 runtime and shared world:
   - `./scripts/bootstrap_mixed_stack.sh`
   - `./scripts/run_ros1_world.sh --scenario scenario_3_maritime_usv_qr`
2. Export truth-level deck/UAV/relative states on ROS 1:
   - `./scripts/run_ros1_platform_interface.sh`
3. Start PX4 ROS 2 transport:
   - `./scripts/run_microxrce_agent.sh`
4. Start `ros1_bridge`:
   - `./scripts/run_ros1_bridge.sh`
5. Start ROS 2 research nodes:
   - `./scripts/run_ros2_research.sh`

For repeatable scenario-level chain validation, prefer the formal validation entrypoint:

- `./scripts/run_chain_validation.sh --scenario scenario_1_static_ground_qr`
- `./scripts/run_chain_validation.sh --scenario scenario_2_ground_moving_qr`
- `./scripts/run_chain_validation.sh --scenario scenario_3_maritime_usv_qr`

The default ROS 2 baseline launch now:

- forces `use_sim_time=true`
- loads a calm-truth scenario config by default
- starts experiment metadata generation and summary logging
- publishes a single `/relative_state/active` input for the task layer
- publishes a single `/controller/reference_active` input for the control layer
- forwards controller commands to PX4 offboard topics through `controller_interface/px4_offboard_bridge`

## Machine-level gaps still expected

On this machine, the following external pieces were not yet present when this migration step was started:

- `px4_msgs`
- `px4_ros_com`

The repository now includes `ros2_px4_ws.repos` and bootstrap scripts so these missing upstream pieces can be installed and built in a controlled way, while `ros1_bridge` is cloned and compiled under the runtime root.

The validated local branch combination on this machine was:

- `px4_msgs` -> `release/1.14`
- `px4_ros_com` -> `release/v1.14`
- `ros1_bridge` -> `foxy`

`PX4_Firmware/Tools/update_px4_ros2_bridge.sh` is left disabled by default in the bootstrap flow because it did not match the validated local `px4_ros_com` tree here.

## Practical build note discovered during setup

Keep ROS 2 workspaces on an ASCII-only filesystem path.

During local verification on this machine, `px4_msgs` failed when built from a workspace under `~/下载/...`, because the ROS 2 interface generation path handling broke on the non-ASCII path component. The same `px4_msgs` and `px4_ros_com` sources built successfully once moved to an ASCII-only path under `/tmp/...`.
