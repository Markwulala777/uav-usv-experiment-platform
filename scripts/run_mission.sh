#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_ROOT="${1:-${INSTALL_ROOT:-$HOME/uav-usv-experiment-platform-runtime}}"

CATKIN_WS="${CATKIN_WS:-$INSTALL_ROOT/catkin_ws}"
XTDRONE_DIR="${XTDRONE_DIR:-$INSTALL_ROOT/XTDrone}"
MISSION_SCRIPT="${MISSION_SCRIPT:-$XTDRONE_DIR/control/usv_drone_mission.py}"

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

if [[ ! -f "$CATKIN_WS/devel/setup.bash" ]]; then
  echo "Missing catkin workspace setup file: $CATKIN_WS/devel/setup.bash" >&2
  echo "Run $REPO_ROOT/scripts/bootstrap.sh first." >&2
  exit 1
fi

if [[ ! -f "$MISSION_SCRIPT" ]]; then
  echo "Missing mission script: $MISSION_SCRIPT" >&2
  echo "Run $REPO_ROOT/scripts/bootstrap.sh first." >&2
  exit 1
fi

source /opt/ros/noetic/setup.bash
source "$CATKIN_WS/devel/setup.bash"

cd "$(dirname "$MISSION_SCRIPT")"
exec python3 "$(basename "$MISSION_SCRIPT")"
