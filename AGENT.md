# Purpose

This file is for Codex and similar coding agents.

Use it to answer four questions before making changes:

- What kind of repository is this?
- Which documents define the ground truth?
- Which directories are the preferred edit targets?
- Which architecture boundaries must not be broken?

This is not a general ROS guide and not a user-facing README.

# Read First

Before any non-trivial change, read these files in this order:

1. `README.md`
2. `docs/MIXED_ROS1_ROS2_ARCHITECTURE.md`
3. `docs/FRAME_CONVENTION.md`
4. `docs/TIME_BASE.md`
5. `docs/BASELINE_ACCEPTANCE.md`

Use them as follows:

- `README.md`
  Read for repository layout, runtime layout, bootstrap flow, pinned versions, and launcher scripts.
- `docs/MIXED_ROS1_ROS2_ARCHITECTURE.md`
  Read for ROS 1 vs ROS 2 vs PX4 vs `ros1_bridge` layer boundaries.
- `docs/FRAME_CONVENTION.md`
  Mandatory for any change involving setpoints, frames, relative state, PX4 offboard, or truth topics.
- `docs/TIME_BASE.md`
  Mandatory for any change involving timestamps, logging, replay, metadata, or simulation time.
- `docs/BASELINE_ACCEPTANCE.md`
  Use as the acceptance contract for "is this change still correct?"

# Platform Baseline

- This repository packages a mixed `ROS 1 + ROS 2 + PX4 + VRX` experiment platform for UAV-USV cooperative landing.
- It is not a full mirror of upstream projects.
- `PX4_Firmware` and `XTDrone` are not fully vendored here.
- `catkin_ws_src/` contains a mix of experiment packages and upstream snapshots.
- `overlays/` contains the experiment-specific PX4 and XTDrone overlays.

Validated target baseline:

- Ubuntu `20.04`
- Gazebo Classic `11`
- ROS 1 `Noetic`
- ROS 2 `Foxy`
- PX4 `v1.14.0`

Do not treat this repository as a generic template for Ubuntu 22.04+, newer ROS distros, or newer PX4 unless the user explicitly asks for migration work.

Default runtime and output locations:

- Runtime root: `~/uav-usv-experiment-platform-runtime`
- Experiment outputs: `~/uav-usv-experiment-runs`

# Repository Map and Ownership

Preferred edit zones:

- `ros2_research_ws_src/*`
- `catkin_ws_src/platform_interface_ros1`
- `scripts/*`
- `overlays/*`
- `docs/*`

Directory roles:

- `ros2_research_ws_src/`
  ROS 2 research layer source. Main packages include `mission_stack_msgs`, `platform_interface`, `relative_estimation`, `mission_manager`, `landing_decision`, `landing_guidance`, `trajectory_planner`, `safety_manager`, `controller_interface`, `touchdown_manager`, `experiment_manager`, `metrics_evaluator`, and `joint_bringup`.
- `catkin_ws_src/platform_interface_ros1`
  ROS 1 truth-export boundary. It consumes `/gazebo/model_states` and republishes a reduced, bridge-friendly truth contract.
- `scripts/`
  Bootstrap, runtime launch, and stop entrypoints.
- `overlays/`
  Experiment-specific overlays applied onto upstream PX4 and XTDrone runtimes.
- `catkin_ws_src/` outside `platform_interface_ros1`
  Usually treat as upstream snapshot or third-party dependency code.

Default ownership rule:

- Prefer experiment-layer fixes first.
- Prefer scripts, launch, config, research nodes, or `platform_interface_ros1` before touching upstream snapshots.
- Only edit vendored upstream snapshot code when the problem cannot reasonably be fixed in the experiment layer or overlays.

Source tree vs runtime tree:

- The repository root is the source of truth for code changes.
- The runtime tree is a generated deployment/work tree.
- Launching day-to-day should happen from the runtime tree after bootstrap.
- Do not treat the runtime copy as the long-term source of truth.
- If you change repository source files, make sure the change is propagated into the runtime tree by rebuild, resync, overlay refresh, or bootstrap.

# Non-Negotiable Invariants

Unless the user explicitly asks for architecture changes, preserve all of the following.

Frame and control boundary:

- Gazebo truth and research-layer truth remain in `world` ENU.
- `relative_estimation` publishes `/relative_state/active` as the single public active-state input.
- `landing_guidance` publishes `/guidance/reference` in `world` ENU semantics only.
- `controller_interface` publishes `/controller/reference_active` as the single public active-reference input.
- `controller_interface/px4_offboard_bridge` is the only allowed conversion point from research-layer coordinates into PX4 control coordinates.
- The only allowed conversion chain is:
  - `world ENU -> local ENU -> local NED`
- Do not add duplicate ENU-to-NED conversion in any upstream node.
- Do not publish PX4 NED setpoints from any node other than `px4_offboard_bridge`.
- `px4_offboard_bridge` resolves PX4 local origin using:
  - `/uav/state_truth`
  - `/fmu/out/vehicle_local_position`

Time boundary:

- Gazebo simulation time is the authoritative ROS-side time source.
- ROS 1 world-side nodes must run with `use_sim_time=true`.
- ROS 2 research-side nodes must run with `use_sim_time=true`.
- PX4 is not a direct consumer of ROS `/clock`.
- Do not reintroduce MAVROS wall/system time sync behavior that fights Gazebo sim time.

Runtime boundary:

- The mixed stack is expected to run from an ASCII-only path.
- Keep `ros2_px4_ws` and `ros2_research_ws` on ASCII-only filesystem paths.
- Do not use paths containing Chinese or other non-ASCII characters for the ROS 2 workspaces.

Acceptance boundary:

- `metrics_evaluator/frame_audit` must pass within configured tolerances.
- `controller_interface` must retain the only PX4/offboard output boundary.
- Each run must still produce metadata, event-log, and summary artifacts.

# Bootstrap and Bring-up

Default mixed-stack bootstrap:

```bash
./scripts/bootstrap_mixed_stack.sh ~/uav-usv-experiment-platform-runtime
```

After bootstrap, prefer launching from the runtime tree, not from the source tree.

Standard five-terminal bring-up order:

1. `~/uav-usv-experiment-platform-runtime/scripts/run_ros1_world.sh --scenario scenario_3_maritime_usv_qr`
2. `~/uav-usv-experiment-platform-runtime/scripts/run_ros1_platform_interface.sh`
3. `~/uav-usv-experiment-platform-runtime/scripts/run_microxrce_agent.sh`
4. `~/uav-usv-experiment-platform-runtime/scripts/run_ros1_bridge.sh`
5. `~/uav-usv-experiment-platform-runtime/scripts/run_ros2_research.sh`

Script roles:

- `run_ros1_world.sh`
  Canonical ROS 1 world selector. Use `--scenario` to choose between the frozen
  scenario 1/2/3 world profiles; it then delegates to `run_sim.sh`.
- `run_ros1_platform_interface.sh`
  Starts `platform_interface_ros1`.
- `run_microxrce_agent.sh`
  Starts `MicroXRCEAgent` on UDP port `8888` by default.
- `run_ros1_bridge.sh`
  Starts `ros1_bridge` using `dynamic_bridge`.
- `run_ros2_research.sh`
  Launches `joint_bringup mission_stack_minimal.launch.py`.
- `run_chain_validation.sh`
  Formal single-entry validation launcher for
  `scenario_1_static_ground_qr`, `scenario_2_ground_moving_qr`, and
  `scenario_3_maritime_usv_qr`. It wraps ROS 1 world startup,
  `platform_interface_ros1`, `MicroXRCEAgent`, `ros1_bridge`, ROS 2 bringup,
  and scenario-specific motion baselines where applicable. Treat it as the
  formal chain-validation entrypoint, not the default day-to-day mission
  runtime entrypoint.
- `run_mission.sh`
  Legacy ROS 1 / XTDrone mission entrypoint. It is not the main mixed-stack research-layer entrypoint.

Default ROS 2 baseline nodes:

- `experiment_manager`
- `platform_interface`
- `relative_estimation`
- `mission_manager`
- `landing_decision`
- `landing_guidance`
- `trajectory_planner`
- `safety_manager`
- `controller_interface`
- `touchdown_manager`
- `metrics_evaluator`

Common environment variables:

- `INSTALL_ROOT`
- `CATKIN_WS`
- `PX4_DIR`
- `XTDRONE_DIR`
- `ROS2_PX4_WS`
- `ROS2_RESEARCH_WS`
- `ROS1_BRIDGE_WS`
- `PX4_MSGS_REF`
- `PX4_ROS_COM_REF`
- `ROS1_BRIDGE_REF`
- `USE_PX4_UPDATE_BRIDGE`

# Validation Checklist

Validate architecture contracts first, then validate local behavior.

Expected run artifacts:

- `run_metadata.json`
- `scenario.yaml`
- `events.jsonl`
- `frame_audit_report.json`
- `geometry_consistency_report.json`
- `summary.json`
- `summary.csv`

Expected output directory shape:

- `~/uav-usv-experiment-runs/<scenario_id>/<run_id>/`

High-value topics to inspect first:

- `/relative_state/active`
- `/mission/phase`
- `/landing_window/status`
- `/landing_decision/status`
- `/controller/reference_active`
- `/metrics/frame_audit/passed`
- `/metrics/frame_audit/report`
- `/metrics/geometry_consistency/passed`
- `/metrics/geometry_consistency/report`
- `/experiment/run_status`
- `/experiment/events`

If the change touches PX4 offboard, frames, or relative state, also inspect:

- `/uav/state_truth`
- `/fmu/out/vehicle_local_position`
- `/relative_state/truth`
- `/controller/command`

Recommended validation order:

1. Confirm the relevant nodes are running.
2. Confirm the expected topics exist and publish data.
3. Confirm `use_sim_time` is still in effect where required.
4. Confirm references are still published in research-layer `world` ENU, not prematurely converted to NED upstream.
5. Confirm `metrics_evaluator/frame_audit` still passes and writes `frame_audit_report.json`.
6. Confirm `metrics_evaluator/geometry_consistency` still passes and writes `geometry_consistency_report.json`.
7. Confirm a full run still writes `summary.json` and `summary.csv`.

Minimum validation by task type:

- ROS 2 research node fix
  Rebuild `ros2_research_ws`, restart `run_ros2_research.sh`, then inspect node logs, topics, and output files.
- Mixed-stack startup debugging
  Verify bootstrap artifacts exist, then bring up terminals in order and isolate the first broken stage.
- Scenario chain-validation debugging
  Prefer `run_chain_validation.sh --scenario ...`, then inspect
  `summary.json.chain_validation_passed`, `frame_audit_report.json`,
  `geometry_consistency_report.json`, and the per-process logs under
  `logs/`.
- PX4/offboard logic change
  Always inspect `/guidance/reference`, `/controller/reference_active`, `/fmu/out/vehicle_local_position`, and `frame_audit_report.json`.

# Change Policy

Favor minimal, local, reproducible changes.

Default change order:

1. Parameters, launch files, configs, scripts, or ROS 2 research nodes
2. `platform_interface_ros1`
3. `overlays/*`
4. Upstream snapshot code

Do not do these by default:

- Do not upgrade Ubuntu, ROS, Gazebo, PX4, VRX, or XTDrone versions unless explicitly asked.
- Do not duplicate frame conversion logic across multiple nodes.
- Do not bypass `px4_offboard_bridge` for PX4 coordinate output.
- Do not patch generated runtime files as the primary fix.

Typical follow-up actions after edits:

- `ros2_research_ws_src/*`
  Rebuild the runtime `ros2_research_ws` with `colcon build --symlink-install`, then restart `run_ros2_research.sh`.
- `catkin_ws_src/platform_interface_ros1` or other catkin packages
  Resync into the runtime tree, rebuild the catkin workspace, then restart affected ROS 1 processes.
- `overlays/*`
  Re-run `scripts/apply_overlay.sh` or the relevant bootstrap flow, then rebuild affected runtime components.
- `scripts/*`
  If the runtime tree already exists, resync the updated scripts into runtime or re-run the relevant bootstrap step.
- `docs/*`
  No rebuild required, but keep documentation aligned with the actual implementation.

If full runtime validation is not feasible, at least do static consistency checks:

- Topic names match the code.
- Launch references point to existing packages and executables.
- Output filenames match the node implementations.
- Documented default paths match the scripts.

# Common Failure Modes

1. Runtime not built

- Symptoms
  Missing `catkin_ws/devel/setup.bash`, `ros2_research_ws/install/setup.bash`, or `PX4_Firmware/build/px4_sitl_default`
- Response
  Re-run `bootstrap.sh` or `bootstrap_mixed_stack.sh`

2. Wrong install root

- Symptoms
  Launch scripts cannot find workspaces, PX4, XTDrone, or install files
- Response
  Check the first script argument and `INSTALL_ROOT`, `CATKIN_WS`, `ROS2_RESEARCH_WS`, `PX4_DIR`, and related environment variables

3. Non-ASCII ROS 2 workspace path

- Symptoms
  `px4_msgs`, `px4_ros_com`, or interface generation fails unexpectedly
- Response
  Move the runtime and ROS 2 workspaces to an ASCII-only path such as `~/uav-usv-experiment-platform-runtime`

4. `ros1_bridge` missing or not bridging

- Symptoms
  ROS 1 truth topics exist but ROS 2 side does not receive the bridged data
- Response
  Confirm `run_ros1_platform_interface.sh` is running, then confirm `run_ros1_bridge.sh` is running, then confirm `ros1_bridge_ws` was successfully built or a system `ros1_bridge` is available

5. Frame boundary violation

- Symptoms
  `metrics_evaluator/frame_audit` fails, relative states disagree, or control data looks double-converted between ENU and NED
- Response
  Check for any conversion outside `controller_interface/px4_offboard_bridge`, and confirm `landing_guidance` still publishes only `world` ENU references

6. Sim-time boundary violation

- Symptoms
  Timestamps look inconsistent, replay is unreliable, or summaries do not line up with the run
- Response
  Confirm ROS 1 and ROS 2 still use `use_sim_time=true`, and do not treat PX4 as a direct ROS `/clock` consumer

7. Output files missing

- Symptoms
  No `run_metadata.json`, `events.jsonl`, `frame_audit_report.json`, `geometry_consistency_report.json`, `summary.json`, or `summary.csv`
- Response
  Check `/experiment/run_status`, then check whether the run reached touchdown or abort, then check output directory permissions and node logs

# Working Norm for Future Codex Runs

- First identify the failing layer:
  - ROS 1 world layer
  - ROS 1 truth bridge
  - ROS 1 / ROS 2 bridge
  - ROS 2 research layer
  - PX4 / offboard layer
  - bootstrap / runtime layer
- Check frame and time invariants before changing code.
- Find the smallest viable fix before expanding into upstream snapshots.
- If the change affects runtime behavior, state which workspace must be rebuilt, which launcher must be restarted, and which artifacts or topics should be checked.
- If docs and implementation disagree, verify against code plus the existing source-of-truth docs before changing the rule.
