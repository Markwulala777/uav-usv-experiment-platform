#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_ROOT="${1:-${INSTALL_ROOT:-$HOME/uav-usv-experiment-platform-runtime}}"

CATKIN_WS="${CATKIN_WS:-$INSTALL_ROOT/catkin_ws}"
PX4_DIR="${PX4_DIR:-$INSTALL_ROOT/PX4_Firmware}"
WORLD_FILE="${WORLD_FILE:-$CATKIN_WS/build/vrx_gazebo/worlds/example_course.world}"
LAUNCH_FILE="${LAUNCH_FILE:-$PX4_DIR/launch/sandisland.launch}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

if [[ ! -f "$CATKIN_WS/devel/setup.bash" ]]; then
  echo "Missing catkin workspace setup file: $CATKIN_WS/devel/setup.bash" >&2
  echo "Run $REPO_ROOT/scripts/bootstrap.sh first." >&2
  exit 1
fi

if [[ ! -f "$WORLD_FILE" ]]; then
  echo "Missing generated world file: $WORLD_FILE" >&2
  echo "Run $REPO_ROOT/scripts/bootstrap.sh first, or rebuild the catkin workspace." >&2
  exit 1
fi

if [[ ! -d "$PX4_DIR/build/px4_sitl_default" ]]; then
  echo "Missing PX4 SITL build directory: $PX4_DIR/build/px4_sitl_default" >&2
  echo "Run $REPO_ROOT/scripts/bootstrap.sh first." >&2
  exit 1
fi

need_cmd xmlstarlet

source /opt/ros/noetic/setup.bash
source "$CATKIN_WS/devel/setup.bash"
export ROS_PACKAGE_PATH="${ROS_PACKAGE_PATH:-}:$PX4_DIR"
source "$PX4_DIR/Tools/setup_gazebo.bash" "$PX4_DIR" "$PX4_DIR/build/px4_sitl_default"

if ! rospack find mavros >/dev/null 2>&1; then
  echo "ROS package 'mavros' was not found. Install ros-noetic-mavros and ros-noetic-mavros-extras." >&2
  exit 1
fi

exec roslaunch "$LAUNCH_FILE" "world:=$WORLD_FILE"
