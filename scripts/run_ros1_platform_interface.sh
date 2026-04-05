#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_INSTALL_ROOT="$HOME/uav-usv-experiment-platform-runtime"

if [[ -d "$SCRIPT_ROOT/catkin_ws" || -d "$SCRIPT_ROOT/PX4_Firmware" ]]; then
  DEFAULT_INSTALL_ROOT="$SCRIPT_ROOT"
fi

INSTALL_ROOT="${1:-${INSTALL_ROOT:-$DEFAULT_INSTALL_ROOT}}"
CATKIN_WS="${CATKIN_WS:-$INSTALL_ROOT/catkin_ws}"
shift $(( $# > 0 ? 1 : 0 ))

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

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

if [[ ! -f "$CATKIN_WS/devel/setup.bash" ]]; then
  echo "Missing catkin workspace setup file: $CATKIN_WS/devel/setup.bash" >&2
  echo "Build or restore the mixed runtime before launching the ROS 1 platform interface." >&2
  exit 1
fi

reset_ros_env
source_setup /opt/ros/noetic/setup.bash
source_setup "$CATKIN_WS/devel/setup.bash"

launch_args=("$@")

if [[ -n "${PLATFORM_MODE:-}" ]]; then
  launch_args+=("platform_mode:=$PLATFORM_MODE")
fi

if [[ -n "${PLATFORM_MODEL:-}" ]]; then
  launch_args+=("platform_model:=$PLATFORM_MODEL")
fi

if [[ -n "${UAV_MODEL:-}" ]]; then
  launch_args+=("uav_model:=$UAV_MODEL")
fi

if [[ -n "${PLATFORM_OFFSET_XYZ:-}" ]]; then
  launch_args+=("platform_offset_xyz:=$PLATFORM_OFFSET_XYZ")
fi

if [[ -n "${LANDING_ZONE_OFFSET_XYZ:-}" ]]; then
  launch_args+=("landing_zone_offset_xyz:=$LANDING_ZONE_OFFSET_XYZ")
fi

exec roslaunch platform_interface_ros1 platform_interface_ros1.launch "${launch_args[@]}"
