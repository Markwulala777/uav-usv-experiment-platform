# mission_stack_msgs

Shared ROS 2 interface contracts for the research layer.

This package owns the public message types used across the mission, decision,
guidance, control, touchdown, experiment, and metrics packages.

## Planner contract highlights

- `/mission/phase` remains the sole authoritative mission phase source.
- `ReferenceTrajectory.phase` and `PlannerStatus.phase` are contextual
  annotations only.
- Planner outputs must use `source=planner`.
- Guidance outputs must use `source=guidance`.
- `planner_backend` carries the backend identity; it must not be folded into
  `source`.
- `ReferenceTrajectory.terminal_target` may represent either a single terminal
  target or a terminal-set summary.
- `LandingZoneState.zone_pose` defines the zone frame/orientation, while
  `LandingZoneState.center_pose` is the default terminal alignment center.

## Controlled source-code values

The following source strings are controlled codes and should not be replaced
with free-form text:

- `truth`
- `estimate`
- `bridge`
- `simulator`
- `mock`
- `recorded`

Typical uses:

- `relative_state_source`: `truth`, `estimate`, `recorded`, `mock`
- `platform_state_source`: `bridge`, `simulator`, `recorded`, `mock`
- `landing_zone_state_source`: `bridge`, `simulator`, `recorded`, `mock`
- `uav_state_source`: `truth`, `estimate`, `bridge`, `recorded`, `mock`

## ControllerReference

`ControllerReference` is the active control reference normalized by
`controller_interface/reference_mux`.

Minimal fields:

- `header`
- `source_type`
- `phase`
- `target_pose`
- `target_twist`
- `terminal_spec`
- `feasible`
- `sequence_id`
- `source`

Recommended `source_type` values:

- `SOURCE_GUIDANCE`
- `SOURCE_TRAJECTORY`

## LandingDecisionStatus.advisory

Recommended fixed values:

- `CONTINUE`
- `HOLD`
- `REPLAN`
- `GO_AROUND`
- `ABORT`
