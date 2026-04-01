#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_INSTALL_ROOT="$HOME/uav-usv-experiment-platform-runtime"

if [[ -d "$SCRIPT_ROOT/catkin_ws" || -d "$SCRIPT_ROOT/PX4_Firmware" ]]; then
  DEFAULT_INSTALL_ROOT="$SCRIPT_ROOT"
fi

INSTALL_ROOT="${1:-${INSTALL_ROOT:-$DEFAULT_INSTALL_ROOT}}"

TARGET_PATTERNS=(
  "roslaunch .*sandisland.launch"
  "roslaunch .*deck_interface_ros1.launch"
  "ros2 launch joint_bringup stage1_joint.launch.py"
  "$INSTALL_ROOT/PX4_Firmware/build/px4_sitl_default/bin/px4"
  "$INSTALL_ROOT/catkin_ws/src/gazebo_ros_pkgs/gazebo_ros/scripts/gzserver"
  "$INSTALL_ROOT/catkin_ws/src/gazebo_ros_pkgs/gazebo_ros/scripts/gzclient"
  "gzserver .*${INSTALL_ROOT}/catkin_ws/build/vrx_gazebo/worlds/example_course.world"
  "gzclient .*${INSTALL_ROOT}/catkin_ws/devel/lib/libgazebo_ros_paths_plugin.so"
  "$INSTALL_ROOT/catkin_ws/devel/.private/deck_interface_ros1/lib/deck_interface_ros1/deck_truth_bridge.py"
  "$INSTALL_ROOT/ros1_bridge_ws/install/ros1_bridge/lib/ros1_bridge/dynamic_bridge"
  "/opt/ros/foxy/bin/ros2 run ros1_bridge dynamic_bridge"
  "$INSTALL_ROOT/ros2_research_ws/install/experiment_manager/lib/experiment_manager/scenario_runner"
  "$INSTALL_ROOT/ros2_research_ws/install/deck_description/lib/deck_description/deck_geometry"
  "$INSTALL_ROOT/ros2_research_ws/install/deck_interface/lib/deck_interface/truth_relay"
  "$INSTALL_ROOT/ros2_research_ws/install/relative_estimation/lib/relative_estimation/truth_relative_state"
  "$INSTALL_ROOT/ros2_research_ws/install/safety_manager/lib/safety_manager/truth_safety_monitor"
  "$INSTALL_ROOT/ros2_research_ws/install/touchdown_manager/lib/touchdown_manager/truth_touchdown_monitor"
  "$INSTALL_ROOT/ros2_research_ws/install/landing_guidance/lib/landing_guidance/truth_guidance"
  "$INSTALL_ROOT/ros2_research_ws/install/landing_guidance/lib/landing_guidance/px4_offboard_bridge"
  "$INSTALL_ROOT/ros2_research_ws/install/frame_audit/lib/frame_audit/truth_frame_audit"
  "$INSTALL_ROOT/ros2_research_ws/install/metrics_evaluator/lib/metrics_evaluator/summary_writer"
  "/opt/ros/noetic/lib/mavros/mavros_node"
  "MicroXRCEAgent udp4 -p 8888"
  "roscore"
  "rosmaster --core"
)

any_matches() {
  local pattern
  for pattern in "${TARGET_PATTERNS[@]}"; do
    if pgrep -af "$pattern" >/dev/null 2>&1; then
      return 0
    fi
  done
  return 1
}

print_matches() {
  local pattern
  for pattern in "${TARGET_PATTERNS[@]}"; do
    pgrep -af "$pattern" 2>/dev/null || true
  done | sort -u
}

signal_matches() {
  local signal="$1"
  local pattern
  for pattern in "${TARGET_PATTERNS[@]}"; do
    pkill "-${signal}" -f "$pattern" 2>/dev/null || true
  done
}

wait_for_exit() {
  local timeout_seconds="$1"
  local waited=0
  while (( waited < timeout_seconds )); do
    if ! any_matches; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  return 1
}

echo "Stopping UAV-USV experiment platform under: $INSTALL_ROOT"

if ! any_matches; then
  echo "No matching experiment-platform processes were found."
  exit 0
fi

echo "Matching processes before shutdown:"
print_matches

echo
echo "Sending SIGINT to experiment-platform processes..."
signal_matches INT
if wait_for_exit 5; then
  echo "Experiment platform stopped cleanly."
  exit 0
fi

echo "Some processes are still running. Sending SIGTERM..."
signal_matches TERM
if wait_for_exit 5; then
  echo "Experiment platform stopped after SIGTERM."
  exit 0
fi

echo "Some processes are still running. Sending SIGKILL..."
signal_matches KILL
sleep 1

if any_matches; then
  echo "Some processes could not be stopped automatically:" >&2
  print_matches >&2
  exit 1
fi

echo "Experiment platform stopped after SIGKILL."
