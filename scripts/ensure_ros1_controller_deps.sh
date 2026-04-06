#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_INSTALL_ROOT="$HOME/uav-landing-experiment-platform-runtime"

if [[ -d "$SCRIPT_ROOT/catkin_ws" || -d "$SCRIPT_ROOT/PX4_Firmware" ]]; then
  DEFAULT_INSTALL_ROOT="$SCRIPT_ROOT"
fi

INSTALL_ROOT="${1:-${INSTALL_ROOT:-$DEFAULT_INSTALL_ROOT}}"
CATKIN_WS="${CATKIN_WS:-$INSTALL_ROOT/catkin_ws}"
ROS_CONTROLLERS_REPO_URL="${ROS_CONTROLLERS_REPO_URL:-https://github.com/ros-controls/ros_controllers.git}"
ROS_CONTROLLERS_REF="${ROS_CONTROLLERS_REF:-noetic-devel}"
FOUR_WHEEL_STEERING_MSGS_REPO_URL="${FOUR_WHEEL_STEERING_MSGS_REPO_URL:-https://github.com/ros-drivers/four_wheel_steering_msgs.git}"
FOUR_WHEEL_STEERING_MSGS_REF="${FOUR_WHEEL_STEERING_MSGS_REF:-master}"
URDF_GEOMETRY_PARSER_REPO_URL="${URDF_GEOMETRY_PARSER_REPO_URL:-https://github.com/ros-controls/urdf_geometry_parser.git}"
URDF_GEOMETRY_PARSER_REF="${URDF_GEOMETRY_PARSER_REF:-kinetic-devel}"
TARGET_DIR="$CATKIN_WS/src/ros_controllers"
FOUR_WHEEL_STEERING_MSGS_DIR="$CATKIN_WS/src/four_wheel_steering_msgs"
URDF_GEOMETRY_PARSER_DIR="$CATKIN_WS/src/urdf_geometry_parser"

source_setup() {
  local setup_file="$1"
  set +u
  source "$setup_file"
  set -u
}

clone_or_checkout() {
  local repo_url="$1"
  local target_dir="$2"
  local repo_ref="$3"
  local label="$4"

  if [[ -d "$target_dir/.git" ]]; then
    echo "[ensure_ros1_controller_deps] Reusing existing $label at $target_dir"
    git -C "$target_dir" fetch --all --tags
  elif [[ -e "$target_dir" ]]; then
    echo "[ensure_ros1_controller_deps] Refusing to use $target_dir because it exists and is not a git repository" >&2
    exit 1
  else
    echo "[ensure_ros1_controller_deps] Cloning $label from $repo_url"
    git clone "$repo_url" "$target_dir"
  fi

  git -C "$target_dir" checkout "$repo_ref"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: $0 [INSTALL_ROOT]"
  echo "Environment overrides: CATKIN_WS, ROS_CONTROLLERS_REPO_URL, ROS_CONTROLLERS_REF, FOUR_WHEEL_STEERING_MSGS_REPO_URL, FOUR_WHEEL_STEERING_MSGS_REF, URDF_GEOMETRY_PARSER_REPO_URL, URDF_GEOMETRY_PARSER_REF"
  exit 0
fi

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

if [[ ! -d "$CATKIN_WS/src" ]]; then
  echo "Missing catkin workspace source directory: $CATKIN_WS/src" >&2
  exit 1
fi

source_setup /opt/ros/noetic/setup.bash

clone_or_checkout "$ROS_CONTROLLERS_REPO_URL" "$TARGET_DIR" "$ROS_CONTROLLERS_REF" "ros_controllers"
clone_or_checkout "$FOUR_WHEEL_STEERING_MSGS_REPO_URL" "$FOUR_WHEEL_STEERING_MSGS_DIR" "$FOUR_WHEEL_STEERING_MSGS_REF" "four_wheel_steering_msgs"
clone_or_checkout "$URDF_GEOMETRY_PARSER_REPO_URL" "$URDF_GEOMETRY_PARSER_DIR" "$URDF_GEOMETRY_PARSER_REF" "urdf_geometry_parser"

echo "[ensure_ros1_controller_deps] Building ros_controllers packages"
(
  cd "$CATKIN_WS"
  catkin config --extend /opt/ros/noetic >/dev/null
  catkin build urdf_geometry_parser velocity_controllers effort_controllers
)

source_setup "$CATKIN_WS/devel/setup.bash"

echo "[ensure_ros1_controller_deps] Verifying packages"
rospack find urdf_geometry_parser >/dev/null
rospack find velocity_controllers >/dev/null
rospack find effort_controllers >/dev/null
echo "[ensure_ros1_controller_deps] Done."
