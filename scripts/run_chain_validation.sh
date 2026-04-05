#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_INSTALL_ROOT="$HOME/uav-usv-experiment-platform-runtime"
source "$SCRIPT_DIR/scenario_world_profiles.sh"

if [[ -d "$SCRIPT_ROOT/catkin_ws" || -d "$SCRIPT_ROOT/PX4_Firmware" ]]; then
  DEFAULT_INSTALL_ROOT="$SCRIPT_ROOT"
fi

INSTALL_ROOT="${INSTALL_ROOT:-$DEFAULT_INSTALL_ROOT}"
SCENARIO_ID=""
OUTPUT_ROOT="${OUTPUT_ROOT:-$HOME/uav-usv-experiment-runs}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
TIMEOUT_SEC="${TIMEOUT_SEC:-}"
TIMEOUT_SPECIFIED=0
WORLD_STARTUP_SEC=12

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      echo "Usage: $0 --scenario <scenario_1_static_ground_qr|scenario_2_ground_moving_qr|scenario_3_maritime_usv_qr> [--install-root PATH] [--output-root PATH] [--run-id ID] [--timeout-sec SEC]"
      exit 0
      ;;
    --scenario)
      SCENARIO_ID="$2"
      shift 2
      ;;
    --install-root)
      INSTALL_ROOT="$2"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --run-id)
      RUN_ID="$2"
      shift 2
      ;;
    --timeout-sec)
      TIMEOUT_SEC="$2"
      TIMEOUT_SPECIFIED=1
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$SCENARIO_ID" ]]; then
  echo "Usage: $0 --scenario <scenario_1_static_ground_qr|scenario_2_ground_moving_qr|scenario_3_maritime_usv_qr> [--install-root PATH] [--output-root PATH] [--run-id ID] [--timeout-sec SEC]" >&2
  exit 1
fi

OUTPUT_ROOT="${OUTPUT_ROOT/#\~/$HOME}"
if [[ "$RUN_ID" =~ ^[0-9_]+$ ]]; then
  RUN_ID="run_${RUN_ID}"
fi
RUN_DIR="$OUTPUT_ROOT/$SCENARIO_ID/$RUN_ID"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

start_process() {
  local name="$1"
  shift
  "$@" >"$LOG_DIR/$name.log" 2>&1 &
  local pid=$!
  echo "$pid $name" >>"$LOG_DIR/pids.txt"
}

cleanup() {
  STOP_PLATFORM_EXCLUDE_PIDS="$$ $PPID" "$SCRIPT_DIR/stop_platform.sh" "$INSTALL_ROOT" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

ROS2_LAUNCH_FILE=""
PLATFORM_MODE=""
PLATFORM_MODEL=""
UAV_MODEL="iris_0"
PLATFORM_OFFSET_XYZ=""
LANDING_ZONE_OFFSET_XYZ=""
START_UGV_MOTION=0

case "$SCENARIO_ID" in
  scenario_1_static_ground_qr)
    ROS2_LAUNCH_FILE="scenario_1_static_ground_qr.launch.py"
    PLATFORM_MODE="static_pad"
    PLATFORM_MODEL="landing1"
    PLATFORM_OFFSET_XYZ="[0.0, 0.0, 0.0]"
    LANDING_ZONE_OFFSET_XYZ="[0.0, 0.0, 0.0]"
    if [[ "$TIMEOUT_SPECIFIED" -eq 0 && -z "$TIMEOUT_SEC" ]]; then
      TIMEOUT_SEC=150
    fi
    ;;
  scenario_2_ground_moving_qr)
    ROS2_LAUNCH_FILE="scenario_2_ground_moving_qr.launch.py"
    PLATFORM_MODE="ground_vehicle"
    PLATFORM_MODEL="ugv_0"
    PLATFORM_OFFSET_XYZ="[0.0, 0.0, 0.0]"
    LANDING_ZONE_OFFSET_XYZ="[0.0, 0.0, 1.25]"
    START_UGV_MOTION=1
    if [[ "$TIMEOUT_SPECIFIED" -eq 0 && -z "$TIMEOUT_SEC" ]]; then
      TIMEOUT_SEC=150
    fi
    ;;
  scenario_3_maritime_usv_qr)
    ROS2_LAUNCH_FILE="scenario_3_maritime_usv_qr.launch.py"
    PLATFORM_MODE="maritime_usv"
    PLATFORM_MODEL="wamv"
    PLATFORM_OFFSET_XYZ="[0.0, 0.0, 1.25]"
    LANDING_ZONE_OFFSET_XYZ="[0.5, 0.0, 1.25]"
    WORLD_STARTUP_SEC=20
    if [[ "$TIMEOUT_SPECIFIED" -eq 0 && -z "$TIMEOUT_SEC" ]]; then
      TIMEOUT_SEC=210
    fi
    ;;
  *)
    echo "Unsupported chain-validation scenario: $SCENARIO_ID" >&2
    exit 1
    ;;
esac

resolve_ros1_world_profile "$INSTALL_ROOT" "$SCENARIO_ID"

if [[ ! -f "$SCENARIO_WORLD_LAUNCH_FILE" ]]; then
  echo "Missing world launch file: $SCENARIO_WORLD_LAUNCH_FILE" >&2
  exit 1
fi

if [[ ! -f "$SCENARIO_WORLD_FILE" ]]; then
  echo "Missing world file: $SCENARIO_WORLD_FILE" >&2
  exit 1
fi

STOP_PLATFORM_EXCLUDE_PIDS="$$ $PPID" "$SCRIPT_DIR/stop_platform.sh" "$INSTALL_ROOT" >/dev/null 2>&1 || true

start_process ros1_world "$SCRIPT_DIR/run_ros1_world.sh" --scenario "$SCENARIO_ID" --install-root "$INSTALL_ROOT"
sleep "$WORLD_STARTUP_SEC"

start_process ros1_platform_interface env \
  PLATFORM_MODE="$PLATFORM_MODE" \
  PLATFORM_MODEL="$PLATFORM_MODEL" \
  UAV_MODEL="$UAV_MODEL" \
  PLATFORM_OFFSET_XYZ="$PLATFORM_OFFSET_XYZ" \
  LANDING_ZONE_OFFSET_XYZ="$LANDING_ZONE_OFFSET_XYZ" \
  "$SCRIPT_DIR/run_ros1_platform_interface.sh" "$INSTALL_ROOT"
sleep 3

start_process microxrce_agent "$SCRIPT_DIR/run_microxrce_agent.sh"
sleep 2

start_process ros1_bridge "$SCRIPT_DIR/run_ros1_bridge.sh" "$INSTALL_ROOT"
sleep 2

start_process ros2_research "$SCRIPT_DIR/run_ros2_research.sh" "$INSTALL_ROOT" \
  "$ROS2_LAUNCH_FILE" "output_root:=$OUTPUT_ROOT" "run_id:=$RUN_ID"

if [[ "$START_UGV_MOTION" -eq 1 ]]; then
  sleep 5
  start_process ugv_motion "$SCRIPT_DIR/run_ugv_motion_baseline.sh" "$INSTALL_ROOT"
fi

deadline=$((SECONDS + TIMEOUT_SEC))
while (( SECONDS < deadline )); do
  if [[ -f "$RUN_DIR/summary.json" && -f "$RUN_DIR/frame_audit_report.json" && -f "$RUN_DIR/geometry_consistency_report.json" ]]; then
    break
  fi
  sleep 2
done

if [[ ! -f "$RUN_DIR/summary.json" || ! -f "$RUN_DIR/frame_audit_report.json" || ! -f "$RUN_DIR/geometry_consistency_report.json" ]]; then
  echo "Timed out waiting for validation artifacts under $RUN_DIR" >&2
  exit 1
fi

python3 - "$RUN_DIR/summary.json" <<'PY'
import json
import sys

summary_path = sys.argv[1]
with open(summary_path, "r", encoding="utf-8") as handle:
    summary = json.load(handle)

chain_pass = bool(summary.get("chain_validation_passed", False))
mission_outcome = summary.get("mission_outcome", "unknown")
print(json.dumps({
    "chain_validation_passed": chain_pass,
    "mission_outcome": mission_outcome,
    "run_id": summary.get("run_id", ""),
    "scenario_id": summary.get("scenario_id", ""),
}, ensure_ascii=True))

if not chain_pass:
    sys.exit(1)
PY
