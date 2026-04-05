#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_INSTALL_ROOT="$HOME/uav-usv-experiment-platform-runtime"

if [[ -d "$SCRIPT_ROOT/ros2_research_ws" || -d "$SCRIPT_ROOT/ros2_px4_ws" ]]; then
  DEFAULT_INSTALL_ROOT="$SCRIPT_ROOT"
fi

INSTALL_ROOT="${1:-${INSTALL_ROOT:-$DEFAULT_INSTALL_ROOT}}"
ROS2_PX4_WS="${ROS2_PX4_WS:-$INSTALL_ROOT/ros2_px4_ws}"
ROS2_RESEARCH_WS="${ROS2_RESEARCH_WS:-$INSTALL_ROOT/ros2_research_ws}"
if [[ $# -ge 1 ]]; then
  shift
fi
ROS2_LAUNCH_FILE="${1:-${ROS2_LAUNCH_FILE:-mission_stack_minimal.launch.py}}"
if [[ $# -ge 1 ]]; then
  shift
fi

source_setup() {
  local setup_file="$1"
  set +u
  source "$setup_file"
  set -u
}

source_best_setup() {
  local prefix="$1"
  if [[ -f "$prefix/local_setup.bash" ]]; then
    source_setup "$prefix/local_setup.bash"
  elif [[ -f "$prefix/setup.bash" ]]; then
    source_setup "$prefix/setup.bash"
  fi
}

reset_ros_env() {
  unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH LD_LIBRARY_PATH PKG_CONFIG_PATH PYTHONPATH
  unset ROS_DISTRO ROS_ETC_DIR ROS_MASTER_URI ROS_PACKAGE_PATH ROS_ROOT ROS_VERSION ROS_PYTHON_VERSION
  unset ROS_LOCALHOST_ONLY ROSLISP_PACKAGE_DIRECTORIES ROS_DOMAIN_ID RMW_IMPLEMENTATION
}

if [[ ! -f /opt/ros/foxy/setup.bash ]]; then
  echo "ROS 2 Foxy was not found at /opt/ros/foxy/setup.bash" >&2
  exit 1
fi

if [[ ! -f "$ROS2_RESEARCH_WS/install/setup.bash" ]]; then
  echo "Missing ROS 2 research workspace install file: $ROS2_RESEARCH_WS/install/setup.bash" >&2
  echo "Build or restore the mixed runtime before launching the ROS 2 research layer." >&2
  exit 1
fi

reset_ros_env
source_setup /opt/ros/foxy/setup.bash

source_best_setup "$ROS2_PX4_WS/install"
source_best_setup "$ROS2_RESEARCH_WS/install"

exec ros2 launch joint_bringup "$ROS2_LAUNCH_FILE" "$@"
