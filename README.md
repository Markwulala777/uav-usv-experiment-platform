# uav-usv-experiment-platform

This repository packages the current UAV-USV cooperative landing experiment into a form that is easier to archive on GitHub and deploy on another Ubuntu machine.

It does not vendor the full `PX4_Firmware` or `XTDrone` trees. Instead, it keeps:

- a snapshot of the ROS catkin workspace source tree in `catkin_ws_src/`
- local experiment-specific overlay files for PX4 in `overlays/PX4_Firmware/`
- local experiment-specific overlay files for XTDrone in `overlays/XTDrone/`
- helper scripts for bootstrap and runtime

## Current upstream pins

- PX4 upstream: `https://github.com/PX4/PX4-Autopilot.git`
- PX4 commit: `46a12a09bf11c8cbafc5ad905996645b4fe1a9df`
- XTDrone upstream: `https://gitee.com/robin_shaun/XTDrone.git`
- XTDrone commit: `62339a816ef815113a0366a62e8aca4be3000f80`
- Target ROS distro: `noetic`
- Target Ubuntu version: `20.04`

## Repository layout

```text
uav-usv-experiment-platform/
├── catkin_ws_src/
├── overlays/
│   ├── PX4_Firmware/
│   └── XTDrone/
├── scripts/
│   ├── apply_overlay.sh
│   ├── bootstrap.sh
│   ├── run_sim.sh
│   └── run_mission.sh
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
2. checks out the pinned commits
3. syncs this repository's `catkin_ws_src/` into the runtime catkin workspace
4. runs `scripts/apply_overlay.sh` to sync the experiment overlay files into PX4 and XTDrone
5. installs the PX4 Python dependencies from `PX4_Firmware/Tools/setup/requirements.txt`
6. builds PX4 SITL
7. builds the ROS catkin workspace

## Prerequisites on a fresh Ubuntu machine

Install Ubuntu 20.04 with ROS Noetic first. This repository assumes you already have a working ROS Noetic environment, ideally `ros-noetic-desktop-full`.

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

## Optional custom install root

All three scripts accept an optional install root as the first argument:

```bash
./scripts/bootstrap.sh /data/uav-usv-experiment-platform-runtime
./scripts/run_sim.sh /data/uav-usv-experiment-platform-runtime
./scripts/run_mission.sh /data/uav-usv-experiment-platform-runtime
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

## Notes for this experiment

- `run_sim.sh` launches the PX4 `sandisland.launch` overlay and explicitly points it to the generated world file in `catkin_ws/build/vrx_gazebo/worlds/example_course.world`.
- `scripts/apply_overlay.sh` can be run by itself if you only want to refresh the PX4 and XTDrone overlay files without rebuilding everything.
- This avoids depending on a pre-generated `example_course.world` file being present under the source package path.
- The mission controller is the XTDrone overlay script `control/usv_drone_mission.py`.
- The default XTDrone upstream is a Gitee URL. If your target machine cannot access Gitee, override `XTDRONE_REPO_URL` when running `scripts/bootstrap.sh`.
- This repository is intended for `Ubuntu 20.04 + ROS Noetic`. It should not be treated as a drop-in deployment package for Ubuntu 22.04 or newer without adaptation.

## Publishing this repository to GitHub

If you are creating the GitHub repository from this machine:

```bash
git remote add origin <your-github-url>
git add .
git commit -m "Initial uav-usv-experiment-platform snapshot"
git push -u origin main
```
