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
PX4_DIR="${PX4_DIR:-$INSTALL_ROOT/PX4_Firmware}"
WORLD_FILE="${WORLD_FILE:-$CATKIN_WS/build/vrx_gazebo/worlds/example_course.world}"
LAUNCH_FILE="${LAUNCH_FILE:-$PX4_DIR/launch/sandisland.launch}"

source_setup() {
  local setup_file="$1"
  set +u
  source "$setup_file"
  set -u
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

filter_colon_var() {
  local var_name="$1"
  local current="${!var_name:-}"
  local filtered=()

  IFS=':' read -r -a parts <<< "$current"
  for part in "${parts[@]}"; do
    [[ -z "$part" ]] && continue

    case "$part" in
      */PX4_Firmware/build/*/build_gazebo*|*/PX4_Firmware/Tools/sitl_gazebo*|*/PX4_Firmware/Tools/simulation/gazebo-classic/*)
        continue
        ;;
    esac

    filtered+=("$part")
  done

  if [[ ${#filtered[@]} -gt 0 ]]; then
    printf -v "$var_name" '%s' "$(IFS=:; echo "${filtered[*]}")"
  else
    printf -v "$var_name" '%s' ""
  fi

  export "$var_name"
}

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

if [[ ! -f "$CATKIN_WS/devel/setup.bash" ]]; then
  echo "Missing catkin workspace setup file: $CATKIN_WS/devel/setup.bash" >&2
  echo "Build or restore the runtime before launching the simulator." >&2
  exit 1
fi

if [[ ! -f "$WORLD_FILE" ]]; then
  echo "Missing generated world file: $WORLD_FILE" >&2
  echo "Rebuild the catkin workspace inside the runtime before launching the simulator." >&2
  exit 1
fi

if [[ ! -d "$PX4_DIR/build/px4_sitl_default" ]]; then
  echo "Missing PX4 SITL build directory: $PX4_DIR/build/px4_sitl_default" >&2
  echo "Build the PX4 runtime before launching the simulator." >&2
  exit 1
fi

need_cmd xmlstarlet

source_setup /opt/ros/noetic/setup.bash
source_setup "$CATKIN_WS/devel/setup.bash"

unset PX4_SIM_MODEL PX4_SIMULATOR PX4_SYS_AUTOSTART PX4_SIM_HOSTNAME PX4_SIM_HOST_ADDR
unset PX4_GZ_MODEL PX4_GZ_MODEL_NAME PX4_GZ_MODEL_POSE PX4_GZ_WORLD PX4_GZ_WORLDS
unset PX4_UXRCE_DDS_NS PX4_UXRCE_DDS_PORT

filter_colon_var LD_LIBRARY_PATH
filter_colon_var GAZEBO_PLUGIN_PATH
filter_colon_var GAZEBO_MODEL_PATH
filter_colon_var GAZEBO_RESOURCE_PATH

if [[ -n "${ROS_PACKAGE_PATH:-}" ]]; then
  export ROS_PACKAGE_PATH="$PX4_DIR:$ROS_PACKAGE_PATH"
else
  export ROS_PACKAGE_PATH="$PX4_DIR"
fi

export GAZEBO_PLUGIN_PATH=""
export GAZEBO_MODEL_PATH=""
export GAZEBO_RESOURCE_PATH=""

if [[ -f "$PX4_DIR/Tools/simulation/gazebo-classic/setup_gazebo.bash" ]]; then
  source "$PX4_DIR/Tools/simulation/gazebo-classic/setup_gazebo.bash" "$PX4_DIR" "$PX4_DIR/build/px4_sitl_default"
elif [[ -f "$PX4_DIR/Tools/setup_gazebo.bash" ]]; then
  set +u
  source "$PX4_DIR/Tools/setup_gazebo.bash" "$PX4_DIR" "$PX4_DIR/build/px4_sitl_default"
  set -u
else
  echo "Missing PX4 Gazebo setup script under $PX4_DIR/Tools" >&2
  exit 1
fi

if ! rospack find mavros >/dev/null 2>&1; then
  echo "ROS package 'mavros' was not found. Install ros-noetic-mavros and ros-noetic-mavros-extras." >&2
  exit 1
fi

exec roslaunch "$LAUNCH_FILE" "world:=$WORLD_FILE"
