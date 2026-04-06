#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_INSTALL_ROOT="$HOME/uav-landing-experiment-platform-runtime"

if [[ -d "$SCRIPT_ROOT/catkin_ws" || -d "$SCRIPT_ROOT/PX4_Firmware" ]]; then
  DEFAULT_INSTALL_ROOT="$SCRIPT_ROOT"
fi

INSTALL_ROOT="${1:-${INSTALL_ROOT:-$DEFAULT_INSTALL_ROOT}}"
EXCLUDE_PID="${STOP_PLATFORM_EXCLUDE_PID:-}"
EXCLUDE_PIDS_RAW="${STOP_PLATFORM_EXCLUDE_PIDS:-}"
declare -A EXCLUDE_PID_SET=()

if [[ -n "$EXCLUDE_PID" ]]; then
  EXCLUDE_PID_SET["$EXCLUDE_PID"]=1
fi

if [[ -n "$EXCLUDE_PIDS_RAW" ]]; then
  for pid in $EXCLUDE_PIDS_RAW; do
    [[ -n "$pid" ]] && EXCLUDE_PID_SET["$pid"]=1
  done
fi

TARGET_PATTERNS=(
  "roslaunch .*sandisland.launch"
  "roslaunch .*zhihang1.launch"
  "roslaunch .*outdoor2_precision_landing.launch"
  "roslaunch .*platform_interface_ros1.launch"
  "run_chain_validation.sh --scenario scenario_1_static_ground_qr"
  "run_chain_validation.sh --scenario scenario_2_ground_moving_qr"
  "ros2 launch joint_bringup baseline_minimal.launch.py"
  "ros2 launch joint_bringup mission_stack_minimal.launch.py"
  "ros2 launch joint_bringup mission_stack_full.launch.py"
  "ros2 launch joint_bringup phase_b_minimal.launch.py"
  "ros2 launch joint_bringup stage1_joint.launch.py"
  "ros2 launch joint_bringup scenario_1_static_ground_qr.launch.py"
  "ros2 launch joint_bringup scenario_2_ground_moving_qr.launch.py"
  "ros2 launch joint_bringup scenario_3_maritime_usv_qr.launch.py"
  "$INSTALL_ROOT/PX4_Firmware/build/px4_sitl_default/bin/px4"
  "$INSTALL_ROOT/catkin_ws/src/gazebo_ros_pkgs/gazebo_ros/scripts/gzserver"
  "$INSTALL_ROOT/catkin_ws/src/gazebo_ros_pkgs/gazebo_ros/scripts/gzclient"
  "gzserver .*${INSTALL_ROOT}/catkin_ws/build/vrx_gazebo/worlds/example_course.world"
  "gzserver .*${INSTALL_ROOT}/XTDrone/sitl_config/worlds/outdoor2.world"
  "gzserver .*${INSTALL_ROOT}/XTDrone/sitl_config/worlds/zhihang1.world"
  "gzclient .*${INSTALL_ROOT}/catkin_ws/devel/lib/libgazebo_ros_paths_plugin.so"
  "$INSTALL_ROOT/catkin_ws/devel/.private/platform_interface_ros1/lib/platform_interface_ros1/platform_truth_bridge.py"
  "$INSTALL_ROOT/ros1_bridge_ws/install/ros1_bridge/lib/ros1_bridge/dynamic_bridge"
  "/opt/ros/foxy/bin/ros2 run ros1_bridge dynamic_bridge"
  "$INSTALL_ROOT/ros2_research_ws/install/experiment_manager/lib/experiment_manager/scenario_runner"
  "$INSTALL_ROOT/ros2_research_ws/install/platform_interface/lib/platform_interface/platform_truth_ingest"
  "$INSTALL_ROOT/ros2_research_ws/install/platform_interface/lib/platform_interface/platform_landing_zone_state"
  "$INSTALL_ROOT/ros2_research_ws/install/platform_interface/lib/platform_interface/platform_uav_truth_provider"
  "$INSTALL_ROOT/ros2_research_ws/install/platform_interface/lib/platform_interface/platform_truth_relay"
  "$INSTALL_ROOT/ros2_research_ws/install/relative_estimation/lib/relative_estimation/truth_relative_state"
  "$INSTALL_ROOT/ros2_research_ws/install/relative_estimation/lib/relative_estimation/active_state_mux"
  "$INSTALL_ROOT/ros2_research_ws/install/mission_manager/lib/mission_manager/phase_manager"
  "$INSTALL_ROOT/ros2_research_ws/install/landing_decision/lib/landing_decision/window_status"
  "$INSTALL_ROOT/ros2_research_ws/install/landing_decision/lib/landing_decision/decision_advisory"
  "$INSTALL_ROOT/ros2_research_ws/install/landing_guidance/lib/landing_guidance/stage_reference"
  "$INSTALL_ROOT/ros2_research_ws/install/landing_guidance/lib/landing_guidance/truth_guidance"
  "$INSTALL_ROOT/ros2_research_ws/install/trajectory_planner/lib/trajectory_planner/moving_deck_planner"
  "$INSTALL_ROOT/ros2_research_ws/install/trajectory_planner/lib/trajectory_planner/trajectory_planner_node"
  "$INSTALL_ROOT/ros2_research_ws/install/safety_manager/lib/safety_manager/safety_monitor"
  "$INSTALL_ROOT/ros2_research_ws/install/safety_manager/lib/safety_manager/reference_filter"
  "$INSTALL_ROOT/ros2_research_ws/install/safety_manager/lib/safety_manager/truth_safety_monitor"
  "$INSTALL_ROOT/ros2_research_ws/install/controller_interface/lib/controller_interface/reference_mux"
  "$INSTALL_ROOT/ros2_research_ws/install/controller_interface/lib/controller_interface/tracking_controller"
  "$INSTALL_ROOT/ros2_research_ws/install/controller_interface/lib/controller_interface/px4_offboard_bridge"
  "$INSTALL_ROOT/ros2_research_ws/install/touchdown_manager/lib/touchdown_manager/contact_monitor"
  "$INSTALL_ROOT/ros2_research_ws/install/touchdown_manager/lib/touchdown_manager/truth_touchdown_monitor"
  "$INSTALL_ROOT/ros2_research_ws/install/metrics_evaluator/lib/metrics_evaluator/summary_writer"
  "$INSTALL_ROOT/ros2_research_ws/install/metrics_evaluator/lib/metrics_evaluator/frame_audit"
  "$INSTALL_ROOT/ros2_research_ws/install/metrics_evaluator/lib/metrics_evaluator/geometry_consistency"
  "$INSTALL_ROOT/scripts/run_ugv_motion_baseline.sh"
  "rostopic pub -r .* /ugv_0/cmd_vel"
  "/opt/ros/noetic/lib/mavros/mavros_node"
  "MicroXRCEAgent udp4 -p 8888"
  "roscore"
  "rosmaster --core"
)

any_matches() {
  local pattern
  local matches
  for pattern in "${TARGET_PATTERNS[@]}"; do
    matches="$(pgrep -af "$pattern" 2>/dev/null || true)"
    if [[ ${#EXCLUDE_PID_SET[@]} -gt 0 ]]; then
      while read -r pid _; do
        [[ -z "${pid:-}" ]] && continue
        if [[ -z "${EXCLUDE_PID_SET[$pid]+x}" ]]; then
          return 0
        fi
      done <<< "$matches"
      continue
    fi
    if [[ -n "$matches" ]]; then
      return 0
    fi
  done
  return 1
}

print_matches() {
  local pattern
  local matches
  for pattern in "${TARGET_PATTERNS[@]}"; do
    matches="$(pgrep -af "$pattern" 2>/dev/null || true)"
    if [[ ${#EXCLUDE_PID_SET[@]} -eq 0 ]]; then
      [[ -n "$matches" ]] && printf '%s\n' "$matches"
      continue
    fi
    while read -r pid rest; do
      [[ -z "${pid:-}" ]] && continue
      if [[ -z "${EXCLUDE_PID_SET[$pid]+x}" ]]; then
        printf '%s %s\n' "$pid" "$rest"
      fi
    done <<< "$matches"
  done | sort -u
}

signal_matches() {
  local signal="$1"
  local pattern
  local pids
  for pattern in "${TARGET_PATTERNS[@]}"; do
    pids="$(pgrep -f "$pattern" 2>/dev/null || true)"
    if [[ -z "$pids" ]]; then
      continue
    fi
    while read -r pid; do
      [[ -z "$pid" ]] && continue
      if [[ -n "${EXCLUDE_PID_SET[$pid]+x}" ]]; then
        continue
      fi
      kill "-${signal}" "$pid" 2>/dev/null || true
    done <<< "$pids"
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
