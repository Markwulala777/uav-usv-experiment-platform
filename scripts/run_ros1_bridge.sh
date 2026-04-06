#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_INSTALL_ROOT="$HOME/uav-landing-experiment-platform-runtime"

if [[ -d "$SCRIPT_ROOT/ros1_bridge_ws" || -d "$SCRIPT_ROOT/ros2_research_ws" ]]; then
  DEFAULT_INSTALL_ROOT="$SCRIPT_ROOT"
fi

INSTALL_ROOT="${1:-${INSTALL_ROOT:-$DEFAULT_INSTALL_ROOT}}"
CATKIN_WS="${CATKIN_WS:-$INSTALL_ROOT/catkin_ws}"
ROS2_PX4_WS="${ROS2_PX4_WS:-$INSTALL_ROOT/ros2_px4_ws}"
ROS2_RESEARCH_WS="${ROS2_RESEARCH_WS:-$INSTALL_ROOT/ros2_research_ws}"
ROS1_BRIDGE_WS="${ROS1_BRIDGE_WS:-$INSTALL_ROOT/ros1_bridge_ws}"

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

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

if [[ ! -f /opt/ros/foxy/setup.bash ]]; then
  echo "ROS 2 Foxy was not found at /opt/ros/foxy/setup.bash" >&2
  exit 1
fi

reset_ros_env
source_setup /opt/ros/noetic/setup.bash

if [[ -f "$CATKIN_WS/devel/setup.bash" ]]; then
  source_setup "$CATKIN_WS/devel/setup.bash"
fi

source_setup /opt/ros/foxy/setup.bash

source_best_setup "$ROS2_PX4_WS/install"
source_best_setup "$ROS2_RESEARCH_WS/install"

if [[ -f "$ROS1_BRIDGE_WS/install/local_setup.bash" || -f "$ROS1_BRIDGE_WS/install/setup.bash" ]]; then
  source_best_setup "$ROS1_BRIDGE_WS/install"
elif ! ros2 pkg prefix ros1_bridge >/dev/null 2>&1; then
  echo "Neither a source-built ros1_bridge workspace nor the system ros1_bridge package was found." >&2
  echo "Build or restore the mixed runtime, or install ros-foxy-ros1-bridge." >&2
  exit 1
fi

exec ros2 run ros1_bridge dynamic_bridge
