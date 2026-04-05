# Frame Convention

This document freezes the current research-baseline frame convention for the mixed ROS1/ROS2 UAV-USV landing stack.

## Goals

- Use one shared Gazebo world frame for truth-level logging and replay.
- Make ENU-to-NED conversion explicit and perform it exactly once.
- Keep deck-relative states reproducible across ROS1, ROS2, and PX4.
- Freeze which layer owns `world` ENU and which layer owns PX4 local NED.

## Canonical frames

- `world`
  - Gazebo shared world frame.
  - Convention: ENU.
  - Used for truth logging, deck truth, and scenario-level metrics.
- `wamv/base_link`
  - Body frame attached to the WAM-V carrier.
  - Used for carrier pose, velocity, and angular-rate interpretation.
- `deck_frame`
  - Deck-fixed frame attached to the landing surface.
  - Used for deck geometry and contact-zone definitions.
- `landing_target_frame`
  - Deck-fixed target frame at the nominal touchdown point.
  - Used for terminal guidance and touchdown evaluation.
- `uav/base_link`
  - UAV body frame.
  - Used for flight-state interpretation and future estimator outputs.
- `camera_*`
  - Onboard sensing frames attached to the UAV camera chain.
  - Reserved for future perception-only experiments.

## Truth publishing responsibilities

- ROS1 `platform_interface_ros1`
  - Publishes deck truth, target truth, UAV truth, and truth relative states.
  - Source topics come from `/gazebo/model_states`.
- ROS2 `platform_interface`
  - Owns `/platform/*` public interfaces and transitional debug truth relays.
- ROS2 `relative_estimation`
  - Recomputes truth relative states and exposes `/relative_state/active`.
- ROS2 `landing_guidance`
  - Publishes stage-wise geometric references in `world` ENU only.
- ROS2 `controller_interface.px4_offboard_bridge`
  - Is the only node allowed to convert research-layer commands into PX4 local NED.

## Relative-state convention

- Relative position is defined as:
  - `uav_position - landing_target_position`
- Truth-level relative position and velocity are expressed in `landing_target_frame`.
- Touchdown classification uses deck-relative states, not world-frame proximity alone.

## Frozen control-coordinate boundary

The only allowed conversion point between research-layer coordinates and PX4 flight-control coordinates in the current baseline is:

- ROS2 `controller_interface.px4_offboard_bridge`

Conversion rules:

- First resolve the PX4 local origin in `world` ENU from:
  - `/uav/state_truth`
  - `/fmu/out/vehicle_local_position`
- Then convert:
  - `world ENU -> local ENU`
  - `local ENU -> local NED`
- Position:
  - `x_ned = y_enu`
  - `y_ned = x_enu`
  - `z_ned = -z_enu`
- Yaw:
  - `yaw_ned = pi/2 - yaw_enu`

Runtime rule during PX4 local-position resets:

- Re-resolve the PX4 local origin in the bridge.
- Keep publishing the OFFBOARD heartbeat.
- Hold the last valid local NED setpoint until a fresh local origin is available.

No other node may silently convert the same state again, publish PX4 setpoints in NED directly, or re-apply the same conversion downstream.

## Audit rules

The `metrics_evaluator/frame_audit` helper checks:

- Target offset consistency between `deck_frame` and `landing_target_frame`
- Relative position consistency between world-frame truth and target-frame truth
- Relative velocity consistency between world-frame truth and target-frame truth

The current baseline is not accepted unless the audit remains within the configured tolerances.
