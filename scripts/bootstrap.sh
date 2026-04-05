#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_ROOT="${1:-${INSTALL_ROOT:-$HOME/uav-usv-experiment-platform-runtime}}"

CATKIN_WS="${CATKIN_WS:-$INSTALL_ROOT/catkin_ws}"
PX4_DIR="${PX4_DIR:-$INSTALL_ROOT/PX4_Firmware}"
XTDRONE_DIR="${XTDRONE_DIR:-$INSTALL_ROOT/XTDrone}"

PX4_REPO_URL="${PX4_REPO_URL:-https://github.com/PX4/PX4-Autopilot.git}"
PX4_REF="${PX4_REF:-v1.14.0}"
XTDRONE_REPO_URL="${XTDRONE_REPO_URL:-https://gitee.com/robin_shaun/XTDrone.git}"
XTDRONE_REF="${XTDRONE_REF:-62339a816ef815113a0366a62e8aca4be3000f80}"
PX4_BUILD_TARGET="${PX4_BUILD_TARGET:-px4_sitl_default}"
PX4_SIM_TARGET="${PX4_SIM_TARGET:-sitl_gazebo-classic}"
SKIP_ROSDEP="${SKIP_ROSDEP:-0}"
SKIP_PX4_PIP="${SKIP_PX4_PIP:-0}"
CMAKE_MODULES_REPO_URL="${CMAKE_MODULES_REPO_URL:-https://github.com/ros/cmake_modules.git}"
CMAKE_MODULES_REF="${CMAKE_MODULES_REF:-0.5-devel}"
TELEOP_TOOLS_REPO_URL="${TELEOP_TOOLS_REPO_URL:-https://github.com/ros-teleop/teleop_tools.git}"
TELEOP_TOOLS_REF="${TELEOP_TOOLS_REF:-noetic-devel}"
VELODYNE_SIMULATOR_REPO_URL="${VELODYNE_SIMULATOR_REPO_URL:-https://github.com/lmark1/velodyne_simulator.git}"
VELODYNE_SIMULATOR_REF="${VELODYNE_SIMULATOR_REF:-master}"
ROS_CONTROLLERS_REPO_URL="${ROS_CONTROLLERS_REPO_URL:-https://github.com/ros-controls/ros_controllers.git}"
ROS_CONTROLLERS_REF="${ROS_CONTROLLERS_REF:-noetic-devel}"
FOUR_WHEEL_STEERING_MSGS_REPO_URL="${FOUR_WHEEL_STEERING_MSGS_REPO_URL:-https://github.com/ros-drivers/four_wheel_steering_msgs.git}"
FOUR_WHEEL_STEERING_MSGS_REF="${FOUR_WHEEL_STEERING_MSGS_REF:-master}"
URDF_GEOMETRY_PARSER_REPO_URL="${URDF_GEOMETRY_PARSER_REPO_URL:-https://github.com/ros-controls/urdf_geometry_parser.git}"
URDF_GEOMETRY_PARSER_REF="${URDF_GEOMETRY_PARSER_REF:-kinetic-devel}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

source_setup() {
  local setup_file="$1"
  set +u
  source "$setup_file"
  set -u
}

reset_ros_env() {
  unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH LD_LIBRARY_PATH PKG_CONFIG_PATH PYTHONPATH
  unset ROS_DISTRO ROS_ETC_DIR ROS_MASTER_URI ROS_PACKAGE_PATH ROS_ROOT ROS_VERSION ROS_PYTHON_VERSION
  unset ROS_LOCALHOST_ONLY ROSLISP_PACKAGE_DIRECTORIES ROS_DOMAIN_ID RMW_IMPLEMENTATION
}

install_runtime_scripts() {
  mkdir -p "$INSTALL_ROOT/scripts"
  rm -f "$INSTALL_ROOT/scripts/run_ros1_deck_interface.sh"
  rsync -a \
    "$REPO_ROOT/scripts/run_chain_validation.sh" \
    "$REPO_ROOT/scripts/scenario_world_profiles.sh" \
    "$REPO_ROOT/scripts/run_sim.sh" \
    "$REPO_ROOT/scripts/run_mission.sh" \
    "$REPO_ROOT/scripts/run_ros1_world.sh" \
    "$REPO_ROOT/scripts/run_ros1_platform_interface.sh" \
    "$REPO_ROOT/scripts/run_microxrce_agent.sh" \
    "$REPO_ROOT/scripts/run_ros1_bridge.sh" \
    "$REPO_ROOT/scripts/run_ros2_research.sh" \
    "$REPO_ROOT/scripts/ensure_ros1_controller_deps.sh" \
    "$REPO_ROOT/scripts/run_ugv_motion_baseline.sh" \
    "$REPO_ROOT/scripts/stop_platform.sh" \
    "$INSTALL_ROOT/scripts/"
  chmod +x "$INSTALL_ROOT/scripts/"*.sh
}

clone_or_checkout() {
  local repo_url="$1"
  local target_dir="$2"
  local repo_ref="$3"
  local label="$4"

  if [[ -d "$target_dir/.git" ]]; then
    echo "[bootstrap] Reusing existing $label at $target_dir"
    if [[ -n "$(git -C "$target_dir" status --short)" ]]; then
      echo "[bootstrap] Cleaning existing $label worktree before checkout"
      git -C "$target_dir" submodule foreach --recursive 'git reset --hard HEAD || true' || true
      git -C "$target_dir" submodule foreach --recursive 'git clean -ffdx || true' || true
      git -C "$target_dir" submodule deinit -f --all || true
      git -C "$target_dir" reset --hard HEAD
      git -C "$target_dir" clean -ffdx
    fi
    git -C "$target_dir" fetch --all --tags
  elif [[ -e "$target_dir" ]]; then
    echo "[bootstrap] Refusing to use $target_dir because it exists and is not a git repository" >&2
    exit 1
  else
    echo "[bootstrap] Cloning $label from $repo_url"
    git clone "$repo_url" "$target_dir"
  fi

  echo "[bootstrap] Checking out $label ref $repo_ref"
  git -C "$target_dir" checkout "$repo_ref"
  git -C "$target_dir" submodule sync --recursive
  git -C "$target_dir" submodule update --init --recursive --force
}

ensure_catkin_support_sources() {
  clone_or_checkout "$CMAKE_MODULES_REPO_URL" "$CATKIN_WS/src/cmake_modules" "$CMAKE_MODULES_REF" "cmake_modules"
  clone_or_checkout "$TELEOP_TOOLS_REPO_URL" "$CATKIN_WS/src/teleop_tools" "$TELEOP_TOOLS_REF" "teleop_tools"
  clone_or_checkout "$VELODYNE_SIMULATOR_REPO_URL" "$CATKIN_WS/src/velodyne_simulator" "$VELODYNE_SIMULATOR_REF" "velodyne_simulator"
  clone_or_checkout "$ROS_CONTROLLERS_REPO_URL" "$CATKIN_WS/src/ros_controllers" "$ROS_CONTROLLERS_REF" "ros_controllers"
  clone_or_checkout "$FOUR_WHEEL_STEERING_MSGS_REPO_URL" "$CATKIN_WS/src/four_wheel_steering_msgs" "$FOUR_WHEEL_STEERING_MSGS_REF" "four_wheel_steering_msgs"
  clone_or_checkout "$URDF_GEOMETRY_PARSER_REPO_URL" "$CATKIN_WS/src/urdf_geometry_parser" "$URDF_GEOMETRY_PARSER_REF" "urdf_geometry_parser"
}

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

need_cmd git
need_cmd rsync
need_cmd make
need_cmd cmake
need_cmd catkin
need_cmd python3
need_cmd ninja

mkdir -p "$INSTALL_ROOT" "$CATKIN_WS/src"

clone_or_checkout "$PX4_REPO_URL" "$PX4_DIR" "$PX4_REF" "PX4"
clone_or_checkout "$XTDRONE_REPO_URL" "$XTDRONE_DIR" "$XTDRONE_REF" "XTDrone"

echo "[bootstrap] Syncing catkin workspace snapshot"
rsync -a --delete "$REPO_ROOT/catkin_ws_src/" "$CATKIN_WS/src/"

echo "[bootstrap] Ensuring supplemental ROS 1 support sources"
ensure_catkin_support_sources

echo "[bootstrap] Applying experiment overlays"
"$SCRIPT_DIR/apply_overlay.sh" "$INSTALL_ROOT"

echo "[bootstrap] Installing runtime launcher scripts"
install_runtime_scripts

source_setup /opt/ros/noetic/setup.bash

if [[ "$SKIP_PX4_PIP" == "1" ]]; then
  echo "[bootstrap] SKIP_PX4_PIP=1, skipping PX4 Python dependency installation"
else
  if ! python3 -m pip --version >/dev/null 2>&1; then
    echo "[bootstrap] python3-pip is required to install PX4 Python dependencies." >&2
    echo "[bootstrap] Install python3-pip, or rerun with SKIP_PX4_PIP=1 if you have already installed them." >&2
    exit 1
  fi

  if [[ -f "$PX4_DIR/Tools/setup/requirements.txt" ]]; then
    echo "[bootstrap] Installing PX4 Python requirements"
    python3 -m pip install --user -r "$PX4_DIR/Tools/setup/requirements.txt"
  else
    echo "[bootstrap] Missing PX4 Python requirements file: $PX4_DIR/Tools/setup/requirements.txt" >&2
    exit 1
  fi
fi

if [[ "$SKIP_ROSDEP" == "1" ]]; then
  echo "[bootstrap] SKIP_ROSDEP=1, skipping rosdep installation"
elif command -v rosdep >/dev/null 2>&1; then
  echo "[bootstrap] Running rosdep for catkin workspace dependencies"
  rosdep install --from-paths "$CATKIN_WS/src" --ignore-src -r -y
else
  echo "[bootstrap] rosdep not found. Install python3-rosdep or rerun with SKIP_ROSDEP=1 if you have already installed dependencies." >&2
  exit 1
fi

echo "[bootstrap] Building PX4 SITL"
(
  reset_ros_env
  cd "$PX4_DIR"
  DONT_RUN=1 make "$PX4_BUILD_TARGET" px4 "$PX4_SIM_TARGET"
)

echo "[bootstrap] Building catkin workspace"
(
  cd "$CATKIN_WS"
  catkin config --extend /opt/ros/noetic
  catkin build
)

echo
echo "[bootstrap] Done."
echo "[bootstrap] Runtime root: $INSTALL_ROOT"
echo "[bootstrap] Start simulator with: $INSTALL_ROOT/scripts/run_sim.sh"
echo "[bootstrap] Start mission with:   $INSTALL_ROOT/scripts/run_mission.sh"
