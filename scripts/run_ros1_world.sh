#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_INSTALL_ROOT="$HOME/uav-usv-experiment-platform-runtime"

if [[ -d "$SCRIPT_ROOT/catkin_ws" || -d "$SCRIPT_ROOT/PX4_Firmware" ]]; then
  DEFAULT_INSTALL_ROOT="$SCRIPT_ROOT"
fi

source "$SCRIPT_DIR/scenario_world_profiles.sh"

usage() {
  echo "Usage: $0 [--scenario <scenario_id>] [--install-root PATH] [legacy_install_root] [legacy_world_launch_file]"
  echo "Supported scenario_id values:"
  echo "  scenario_1_static_ground_qr"
  echo "  scenario_2_ground_moving_qr"
  echo "  scenario_3_maritime_usv_qr"
}

INSTALL_ROOT="${INSTALL_ROOT:-$DEFAULT_INSTALL_ROOT}"
SCENARIO_ID=""
LEGACY_WORLD_LAUNCH_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --scenario)
      [[ $# -lt 2 ]] && { echo "Missing value for --scenario" >&2; usage >&2; exit 1; }
      SCENARIO_ID="$2"
      shift 2
      ;;
    --install-root)
      [[ $# -lt 2 ]] && { echo "Missing value for --install-root" >&2; usage >&2; exit 1; }
      INSTALL_ROOT="$2"
      shift 2
      ;;
    *)
      if [[ "$INSTALL_ROOT" == "$DEFAULT_INSTALL_ROOT" ]]; then
        INSTALL_ROOT="$1"
      elif [[ -z "$LEGACY_WORLD_LAUNCH_FILE" ]]; then
        LEGACY_WORLD_LAUNCH_FILE="$1"
      else
        echo "Unknown argument: $1" >&2
        usage >&2
        exit 1
      fi
      shift
      ;;
  esac
done

WORLD_LAUNCH_FILE="${LEGACY_WORLD_LAUNCH_FILE:-${ROS1_WORLD_LAUNCH_FILE:-}}"
WORLD_FILE="${ROS1_WORLD_FILE:-}"

if [[ -n "$SCENARIO_ID" ]]; then
  if [[ -n "$WORLD_LAUNCH_FILE" || -n "$WORLD_FILE" ]]; then
    echo "--scenario cannot be combined with explicit ROS1 world overrides." >&2
    exit 1
  fi
  resolve_ros1_world_profile "$INSTALL_ROOT" "$SCENARIO_ID"
  WORLD_LAUNCH_FILE="$SCENARIO_WORLD_LAUNCH_FILE"
  WORLD_FILE="$SCENARIO_WORLD_FILE"
fi

if [[ -n "$WORLD_LAUNCH_FILE" ]]; then
  export LAUNCH_FILE="$WORLD_LAUNCH_FILE"
  if [[ -n "$WORLD_FILE" ]]; then
    export WORLD_FILE="$WORLD_FILE"
  fi
  if [[ ! -f "$LAUNCH_FILE" ]]; then
    echo "Missing world launch file: $LAUNCH_FILE" >&2
    exit 1
  fi
  if [[ -n "${WORLD_FILE:-}" && ! -f "$WORLD_FILE" ]]; then
    echo "Missing world file: $WORLD_FILE" >&2
    exit 1
  fi
  exec "$SCRIPT_DIR/run_sim.sh" "$INSTALL_ROOT"
fi

exec "$SCRIPT_DIR/run_sim.sh" "$INSTALL_ROOT"
