# uav-usv-experiment-platform

This repository packages the current UAV-USV cooperative landing experiment into a form that is easier to archive on GitHub and deploy on another Ubuntu machine.

It does not vendor the full `PX4_Firmware` or `XTDrone` trees. Instead, it keeps:

- a snapshot of the ROS catkin workspace source tree in `catkin_ws_src/`
- local experiment-specific overlay files for PX4 in `overlays/PX4_Firmware/`
- local experiment-specific overlay files for XTDrone in `overlays/XTDrone/`
- helper scripts for bootstrap and runtime

## Validated platform target

- Ubuntu: `20.04`
- Gazebo: `Gazebo Classic 11`
- ROS 1 world layer: `Noetic`
- ROS 2 research layer: `Foxy`
- PX4 upstream: `https://github.com/PX4/PX4-Autopilot.git`
- PX4 ref used by bootstrap: `v1.14.0`
- XTDrone upstream: `https://gitee.com/robin_shaun/XTDrone.git`
- XTDrone commit: `62339a816ef815113a0366a62e8aca4be3000f80`
- World carrier: `VRX / ROS 1`
- Research-control carrier: `ROS 2`

The runtime PX4 worktree becomes `v1.14.0-dirty` after this repository's overlay files are applied. That is expected for this platform.

## Repository layout

```text
uav-usv-experiment-platform/
├── catkin_ws_src/
├── ros2_research_ws_src/
├── overlays/
│   ├── PX4_Firmware/
│   └── XTDrone/
├── scripts/
│   ├── apply_overlay.sh
│   ├── bootstrap.sh
│   ├── bootstrap_mixed_stack.sh
│   ├── run_ros1_world.sh
│   ├── run_ros1_deck_interface.sh
│   ├── run_microxrce_agent.sh
│   ├── run_ros1_bridge.sh
│   ├── run_ros2_research.sh
│   ├── run_sim.sh
│   └── run_mission.sh
├── docs/
├── ros2_px4_ws.repos
├── README.md
└── .gitignore
```

## What gets deployed

`scripts/bootstrap.sh` creates a runtime workspace outside this repository by default:

- `~/uav-usv-experiment-platform-runtime/catkin_ws`
- `~/uav-usv-experiment-platform-runtime/PX4_Firmware`
- `~/uav-usv-experiment-platform-runtime/XTDrone`

The script then:

1. clones PX4 and XTDrone from their upstream repositories
2. checks out the pinned upstream refs
3. syncs this repository's `catkin_ws_src/` into the runtime catkin workspace
4. runs `scripts/apply_overlay.sh` to sync the experiment overlay files into PX4 and XTDrone
5. installs the PX4 Python dependencies from `PX4_Firmware/Tools/setup/requirements.txt`
6. builds PX4 SITL
7. builds the ROS catkin workspace

## Mixed ROS1/ROS2 architecture

The repository carries the mixed-architecture split discussed in the design documents:

- ROS 1 Noetic / Gazebo Classic 11 / VRX remain the environment carrier
- ROS 2 Foxy becomes the research-control layer
- PX4 v1.14.0 remains the flight-control carrier
- `ros1_bridge` is built from source and used only for a reduced truth-level interface contract
- `MicroXRCEAgent` remains the PX4 <-> ROS 2 transport entry point

New source and bootstrap entry points:

- `ros2_research_ws_src/`
- `ros2_px4_ws.repos`
- `ros1_bridge_ws` (created under the runtime root by the bootstrap script)
- `scripts/bootstrap_mixed_stack.sh`
- `scripts/run_ros1_world.sh`
- `scripts/run_ros1_deck_interface.sh`
- `scripts/run_microxrce_agent.sh`
- `scripts/run_ros1_bridge.sh`
- `scripts/run_ros2_research.sh`

See `docs/MIXED_ROS1_ROS2_ARCHITECTURE.md` for the new layer split and bring-up order.

## Frozen coordinate and time convention

Phase 1 freezes both coordinate ownership and simulation-time ownership so the research stack stays reproducible across ROS 1, ROS 2, Gazebo, and PX4.

Coordinate boundary:

- Gazebo truth and research-layer truth stay in `world` ENU.
- `deck_interface_ros1` extracts truth from `/gazebo/model_states` and publishes deck, landing-target, UAV, and relative states without converting them into PX4 coordinates.
- `landing_guidance` publishes `/landing_guidance/setpoint/world` in `world` ENU only.
- `landing_guidance/px4_offboard_bridge` is the only node allowed to touch PX4 control coordinates.
- The bridge resolves the PX4 local origin in `world` ENU from `/deck_interface/truth/uav_pose` and `/fmu/out/vehicle_local_position`.
- The bridge then performs exactly one conversion chain: `world ENU -> local ENU -> local NED`.
- No other node in this repository should publish PX4 setpoints in NED or re-apply ENU-to-NED conversion.

Operational consequences for coordinates:

- If PX4 local position resets, the bridge re-resolves the local origin instead of changing the research-layer frame convention.
- During local-origin re-resolution, the bridge keeps publishing the OFFBOARD heartbeat and holds the last valid local NED setpoint instead of going silent.
- This keeps the research-layer contract stable while reducing OFFBOARD dropouts caused by transient PX4 local-position resets.

Time base boundary:

- Gazebo is the simulation clock source for the ROS side of the platform.
- The ROS 1 world launch enables `use_sim_time=true`, so ROS 1 nodes follow Gazebo `/clock`.
- The ROS 2 Stage 1 launch also sets `use_sim_time=true`, so ROS 2 research nodes follow the same Gazebo `/clock`.
- This means ROS 1 world nodes and ROS 2 research nodes share one simulation-time basis during runtime and replay.
- PX4 does not directly subscribe to ROS `use_sim_time`; instead, PX4 stays aligned to the simulator through the SITL transport and PX4-side simulator timing.
- MAVROS wall/system time synchronization is disabled in the PX4 world launch overlay so it does not fight Gazebo simulation time.

Operational consequences for time:

- ROS1 and ROS2 logs should be interpreted on Gazebo simulation time.
- PX4 status should be treated as simulator-synchronized, but not as a ROS `/clock` consumer.
- If Gazebo is paused, reset, or jumps in time, ROS nodes will reflect that jump because they are intentionally using simulation time.

See `docs/FRAME_CONVENTION.md` for the detailed frame definitions and audit rules, and `docs/MIXED_ROS1_ROS2_ARCHITECTURE.md` for the layer boundaries.

For ROS 2 workspaces, prefer an ASCII-only path such as `~/uav-usv-experiment-platform-runtime` and avoid non-ASCII paths like `~/下载/...`, because `px4_msgs` interface generation was observed to fail under a non-ASCII workspace path on this machine.

The mixed bootstrap defaults to the local source combination that was validated on this machine:

- `px4_msgs` -> `release/1.14`
- `px4_ros_com` -> `release/v1.14`
- `ros1_bridge` -> `foxy`

It also skips `PX4_Firmware/Tools/update_px4_ros2_bridge.sh` by default, because that helper was not compatible with the validated local `px4_ros_com` tree here. You can re-enable it with `USE_PX4_UPDATE_BRIDGE=1` if you explicitly want to try that path.

## Prerequisites on a fresh Ubuntu machine

Install Ubuntu 20.04 with both ROS Noetic and ROS 2 Foxy first. This repository assumes you already have a working ROS 1 Noetic environment, ideally `ros-noetic-desktop-full`, and a working ROS 2 Foxy environment under `/opt/ros/foxy`.

Then install the common build tools and runtime packages:

```bash
sudo apt update
sudo apt install -y \
  git rsync build-essential cmake ninja-build xmlstarlet \
  python3-catkin-tools python3-rosdep python3-vcstool \
  python3-osrf-pycommon python3-rosinstall-generator python3-pip \
  ros-noetic-mavros ros-noetic-mavros-extras
```

If `rosdep` has not been initialized yet:

```bash
sudo rosdep init
rosdep update
```

## Quick start

Clone this repository:

```bash
git clone <your-github-url> uav-usv-experiment-platform
cd uav-usv-experiment-platform
```

Bootstrap the runtime workspace:

```bash
./scripts/bootstrap.sh
```

If you have already installed all ROS package dependencies manually, you can skip `rosdep`:

```bash
SKIP_ROSDEP=1 ./scripts/bootstrap.sh
```

If you have already installed the PX4 Python requirements manually, you can skip that step too:

```bash
SKIP_PX4_PIP=1 ./scripts/bootstrap.sh
```

Start the simulator in terminal 1:

```bash
./scripts/run_sim.sh
```

After Gazebo is stable, start the mission controller in terminal 2:

```bash
./scripts/run_mission.sh
```

## Mixed ROS1/ROS2 quick start

Bootstrap the mixed runtime on an ASCII-only path:

```bash
./scripts/bootstrap_mixed_stack.sh ~/uav-usv-experiment-platform-runtime
```

Then start the five runtime terminals in order:

```bash
~/uav-usv-experiment-platform-runtime/scripts/run_ros1_world.sh
~/uav-usv-experiment-platform-runtime/scripts/run_ros1_deck_interface.sh
~/uav-usv-experiment-platform-runtime/scripts/run_microxrce_agent.sh
~/uav-usv-experiment-platform-runtime/scripts/run_ros1_bridge.sh
~/uav-usv-experiment-platform-runtime/scripts/run_ros2_research.sh
```

After bootstrap, the runtime directory carries its own `scripts/` folder. Day-to-day launching can stay entirely inside the runtime tree, and you no longer need to call the source-repository path just to start the platform.

## Optional custom install root

The runtime scripts accept an optional install root as the first argument:

```bash
./scripts/bootstrap.sh /data/uav-usv-experiment-platform-runtime
./scripts/run_sim.sh /data/uav-usv-experiment-platform-runtime
./scripts/run_mission.sh /data/uav-usv-experiment-platform-runtime
./scripts/bootstrap_mixed_stack.sh /data/uav-usv-experiment-platform-runtime
./scripts/run_ros1_world.sh /data/uav-usv-experiment-platform-runtime
./scripts/run_ros1_deck_interface.sh /data/uav-usv-experiment-platform-runtime
./scripts/run_ros1_bridge.sh /data/uav-usv-experiment-platform-runtime
./scripts/run_ros2_research.sh /data/uav-usv-experiment-platform-runtime
```

You can also override these environment variables when needed:

- `INSTALL_ROOT`
- `CATKIN_WS`
- `PX4_DIR`
- `XTDRONE_DIR`
- `PX4_REPO_URL`
- `XTDRONE_REPO_URL`
- `PX4_REF`
- `XTDRONE_REF`
- `SKIP_ROSDEP`
- `SKIP_PX4_PIP`
- `ROS2_PX4_WS`
- `ROS2_RESEARCH_WS`
- `ROS1_BRIDGE_WS`
- `PX4_MSGS_REF`
- `PX4_ROS_COM_REF`
- `ROS1_BRIDGE_REPO_URL`
- `ROS1_BRIDGE_REF`
- `USE_PX4_UPDATE_BRIDGE`

## Notes for this experiment

- `run_sim.sh` launches the PX4 `sandisland.launch` overlay and explicitly points it to the generated world file in `catkin_ws/build/vrx_gazebo/worlds/example_course.world`.
- `scripts/apply_overlay.sh` can be run by itself if you only want to refresh the PX4 and XTDrone overlay files without rebuilding everything.
- This avoids depending on a pre-generated `example_course.world` file being present under the source package path.
- The mission controller is the XTDrone overlay script `control/usv_drone_mission.py`.
- The default XTDrone upstream is a Gitee URL. If your target machine cannot access Gitee, override `XTDRONE_REPO_URL` when running `scripts/bootstrap.sh`.
- The mixed bootstrap builds `ros1_bridge` from source inside the runtime, so it does not require the binary `ros-foxy-ros1-bridge` package to be installable on the host machine.
- The frozen coordinate rule for the mixed stack is: research nodes stay in `world` ENU, and only `landing_guidance/px4_offboard_bridge` converts setpoints into PX4 local NED.
- This repository is intended for `Ubuntu 20.04 + Gazebo Classic 11 + ROS 1 Noetic + ROS 2 Foxy`, with the VRX main world on ROS 1 and the research layer on ROS 2. It should not be treated as a drop-in deployment package for Ubuntu 22.04 or newer without adaptation.
