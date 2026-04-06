#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_INSTALL_ROOT="$HOME/uav-landing-experiment-platform-runtime"

if [[ -d "$SCRIPT_ROOT/catkin_ws" || -d "$SCRIPT_ROOT/PX4_Firmware" ]]; then
  DEFAULT_INSTALL_ROOT="$SCRIPT_ROOT"
fi

INSTALL_ROOT="${1:-${INSTALL_ROOT:-$DEFAULT_INSTALL_ROOT}}"
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: $0 [INSTALL_ROOT]"
  echo "Environment overrides: UGV_CMD_TOPIC, UGV_MODEL_NAME, UGV_GAZEBO_FALLBACK_MODE(auto|always|never), UGV_MOTION_PUB_RATE_HZ, UGV_MOTION_WARMUP_SEC, UGV_MOTION_DURATION_SEC, UGV_MOTION_LINEAR_X, UGV_MOTION_ANGULAR_Z"
  exit 0
fi
if [[ $# -ge 1 ]]; then
  shift
fi
CATKIN_WS="${CATKIN_WS:-$INSTALL_ROOT/catkin_ws}"
CMD_TOPIC="${UGV_CMD_TOPIC:-/ugv_0/cmd_vel}"
MODEL_NAME="${UGV_MODEL_NAME:-ugv_0}"
FALLBACK_MODE="${UGV_GAZEBO_FALLBACK_MODE:-auto}"
PUB_RATE_HZ="${UGV_MOTION_PUB_RATE_HZ:-10}"
WARMUP_SEC="${UGV_MOTION_WARMUP_SEC:-5}"
MOTION_DURATION_SEC="${UGV_MOTION_DURATION_SEC:-10}"
LINEAR_X="${UGV_MOTION_LINEAR_X:-0.3}"
ANGULAR_Z="${UGV_MOTION_ANGULAR_Z:-0.0}"

source_setup() {
  local setup_file="$1"
  set +u
  source "$setup_file"
  set -u
}

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

if [[ ! -f "$CATKIN_WS/devel/setup.bash" ]]; then
  echo "Missing catkin workspace setup file: $CATKIN_WS/devel/setup.bash" >&2
  exit 1
fi

source_setup /opt/ros/noetic/setup.bash
source_setup "$CATKIN_WS/devel/setup.bash"

controller_chain_ready() {
  local service_name="/${MODEL_NAME}/controller_manager/list_controllers"
  local response

  if ! rosservice list 2>/dev/null | grep -qx "$service_name"; then
    return 1
  fi

  response="$(rosservice call "$service_name" 2>/dev/null || true)"
  [[ -z "$response" ]] && return 1

  if grep -q "joint1_velocity_controller" <<< "$response" \
    && grep -q "joint2_velocity_controller" <<< "$response" \
    && grep -q "state: running" <<< "$response"; then
    return 0
  fi

  return 1
}

deadline=$((SECONDS + 30))
while (( SECONDS < deadline )); do
  if rosservice list 2>/dev/null | grep -qx '/gazebo/set_model_state'; then
    break
  fi
  sleep 1
done

if ! rosservice list 2>/dev/null | grep -qx '/gazebo/set_model_state'; then
  echo "Timed out waiting for /gazebo/set_model_state" >&2
  exit 1
fi

sleep "$WARMUP_SEC"

set +e
timeout "${MOTION_DURATION_SEC}s" rostopic pub -r "$PUB_RATE_HZ" "$CMD_TOPIC" geometry_msgs/Twist \
  "{linear: {x: $LINEAR_X, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: $ANGULAR_Z}}" >/dev/null 2>&1 &
cmd_pub_pid=$!

use_gazebo_fallback=0
case "$FALLBACK_MODE" in
  always)
    use_gazebo_fallback=1
    ;;
  never)
    use_gazebo_fallback=0
    ;;
  auto)
    if controller_chain_ready; then
      use_gazebo_fallback=0
    else
      use_gazebo_fallback=1
    fi
    ;;
  *)
    echo "Unsupported UGV_GAZEBO_FALLBACK_MODE: $FALLBACK_MODE" >&2
    kill "$cmd_pub_pid" 2>/dev/null || true
    wait "$cmd_pub_pid" 2>/dev/null || true
    exit 1
    ;;
esac

if [[ "$use_gazebo_fallback" -eq 1 ]]; then
  echo "[run_ugv_motion_baseline] Using Gazebo model-state fallback (mode=$FALLBACK_MODE, model=$MODEL_NAME, topic=$CMD_TOPIC)"
else
  echo "[run_ugv_motion_baseline] Using catvehicle controller chain only (mode=$FALLBACK_MODE, model=$MODEL_NAME, topic=$CMD_TOPIC)"
fi

python_status=0
if [[ "$use_gazebo_fallback" -eq 1 ]]; then
  python3 - "$MODEL_NAME" "$PUB_RATE_HZ" "$MOTION_DURATION_SEC" "$LINEAR_X" <<'PY'
import math
import sys

import rospy
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import GetModelState, SetModelState


def quat_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def main():
    model_name = sys.argv[1]
    pub_rate_hz = float(sys.argv[2])
    duration_sec = float(sys.argv[3])
    linear_x = float(sys.argv[4])

    rospy.init_node("ugv_motion_baseline_driver", anonymous=True)
    rospy.wait_for_service("/gazebo/get_model_state", timeout=15.0)
    rospy.wait_for_service("/gazebo/set_model_state", timeout=15.0)

    get_model_state = rospy.ServiceProxy("/gazebo/get_model_state", GetModelState)
    set_model_state = rospy.ServiceProxy("/gazebo/set_model_state", SetModelState)

    initial = get_model_state(model_name, "world")
    if not initial.success:
        raise RuntimeError(f"failed to query model state for {model_name}: {initial.status_message}")

    x0 = initial.pose.position.x
    y0 = initial.pose.position.y
    z0 = initial.pose.position.z
    yaw0 = quat_to_yaw(initial.pose.orientation)
    dx = linear_x * math.cos(yaw0)
    dy = linear_x * math.sin(yaw0)

    state = ModelState()
    state.model_name = model_name
    state.reference_frame = "world"
    state.pose = initial.pose
    state.twist = initial.twist
    state.twist.linear.x = dx
    state.twist.linear.y = dy
    state.twist.linear.z = 0.0
    state.twist.angular.x = 0.0
    state.twist.angular.y = 0.0
    state.twist.angular.z = 0.0

    rate = rospy.Rate(pub_rate_hz)
    steps = max(int(duration_sec * pub_rate_hz), 1)
    for step in range(1, steps + 1):
        elapsed = step / pub_rate_hz
        state.pose.position.x = x0 + dx * elapsed
        state.pose.position.y = y0 + dy * elapsed
        state.pose.position.z = z0
        result = set_model_state(state)
        if not result.success:
            raise RuntimeError(f"failed to set model state for {model_name}: {result.status_message}")
        rate.sleep()

    state.twist.linear.x = 0.0
    state.twist.linear.y = 0.0
    state.twist.linear.z = 0.0
    state.twist.angular.x = 0.0
    state.twist.angular.y = 0.0
    state.twist.angular.z = 0.0
    set_model_state(state)


if __name__ == "__main__":
    main()
PY
  python_status=$?
fi

wait "$cmd_pub_pid"
cmd_status=$?
set -e

if [[ "$python_status" -ne 0 ]]; then
  echo "UGV Gazebo motion fallback failed with status $python_status" >&2
  exit "$python_status"
fi

if [[ "$cmd_status" -ne 0 && "$cmd_status" -ne 124 ]]; then
  echo "UGV /cmd_vel baseline publisher failed with status $cmd_status" >&2
  exit "$cmd_status"
fi

rostopic pub -1 "$CMD_TOPIC" geometry_msgs/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" >/dev/null 2>&1 || true
