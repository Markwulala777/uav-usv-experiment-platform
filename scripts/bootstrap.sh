#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_ROOT="${1:-${INSTALL_ROOT:-$HOME/uav-usv-experiment-platform-runtime}}"

CATKIN_WS="${CATKIN_WS:-$INSTALL_ROOT/catkin_ws}"
PX4_DIR="${PX4_DIR:-$INSTALL_ROOT/PX4_Firmware}"
XTDRONE_DIR="${XTDRONE_DIR:-$INSTALL_ROOT/XTDrone}"

PX4_REPO_URL="${PX4_REPO_URL:-https://github.com/PX4/PX4-Autopilot.git}"
PX4_REF="${PX4_REF:-46a12a09bf11c8cbafc5ad905996645b4fe1a9df}"
XTDRONE_REPO_URL="${XTDRONE_REPO_URL:-https://gitee.com/robin_shaun/XTDrone.git}"
XTDRONE_REF="${XTDRONE_REF:-62339a816ef815113a0366a62e8aca4be3000f80}"
PX4_BUILD_TARGET="${PX4_BUILD_TARGET:-px4_sitl_default}"
PX4_SIM_TARGET="${PX4_SIM_TARGET:-gazebo}"
SKIP_ROSDEP="${SKIP_ROSDEP:-0}"
SKIP_PX4_PIP="${SKIP_PX4_PIP:-0}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

clone_or_checkout() {
  local repo_url="$1"
  local target_dir="$2"
  local repo_ref="$3"
  local label="$4"

  if [[ -d "$target_dir/.git" ]]; then
    echo "[bootstrap] Reusing existing $label at $target_dir"
    git -C "$target_dir" fetch --all --tags
  elif [[ -e "$target_dir" ]]; then
    echo "[bootstrap] Refusing to use $target_dir because it exists and is not a git repository" >&2
    exit 1
  else
    echo "[bootstrap] Cloning $label from $repo_url"
    git clone "$repo_url" "$target_dir"
  fi

  echo "[bootstrap] Checking out $label ref $repo_ref"
  git -C "$target_dir" checkout "$repo_ref"
  git -C "$target_dir" submodule update --init --recursive
}

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

need_cmd git
need_cmd rsync
need_cmd make
need_cmd cmake
need_cmd catkin
need_cmd python3
need_cmd ninja

mkdir -p "$INSTALL_ROOT" "$CATKIN_WS/src"

clone_or_checkout "$PX4_REPO_URL" "$PX4_DIR" "$PX4_REF" "PX4"
clone_or_checkout "$XTDRONE_REPO_URL" "$XTDRONE_DIR" "$XTDRONE_REF" "XTDrone"

echo "[bootstrap] Syncing catkin workspace snapshot"
rsync -a --delete "$REPO_ROOT/catkin_ws_src/" "$CATKIN_WS/src/"

echo "[bootstrap] Applying experiment overlays"
"$SCRIPT_DIR/apply_overlay.sh" "$INSTALL_ROOT"

source /opt/ros/noetic/setup.bash

if [[ "$SKIP_PX4_PIP" == "1" ]]; then
  echo "[bootstrap] SKIP_PX4_PIP=1, skipping PX4 Python dependency installation"
else
  if ! python3 -m pip --version >/dev/null 2>&1; then
    echo "[bootstrap] python3-pip is required to install PX4 Python dependencies." >&2
    echo "[bootstrap] Install python3-pip, or rerun with SKIP_PX4_PIP=1 if you have already installed them." >&2
    exit 1
  fi

  if [[ -f "$PX4_DIR/Tools/setup/requirements.txt" ]]; then
    echo "[bootstrap] Installing PX4 Python requirements"
    python3 -m pip install --user -r "$PX4_DIR/Tools/setup/requirements.txt"
  else
    echo "[bootstrap] Missing PX4 Python requirements file: $PX4_DIR/Tools/setup/requirements.txt" >&2
    exit 1
  fi
fi

if [[ "$SKIP_ROSDEP" == "1" ]]; then
  echo "[bootstrap] SKIP_ROSDEP=1, skipping rosdep installation"
elif command -v rosdep >/dev/null 2>&1; then
  echo "[bootstrap] Running rosdep for catkin workspace dependencies"
  rosdep install --from-paths "$CATKIN_WS/src" --ignore-src -r -y
else
  echo "[bootstrap] rosdep not found. Install python3-rosdep or rerun with SKIP_ROSDEP=1 if you have already installed dependencies." >&2
  exit 1
fi

echo "[bootstrap] Building PX4 SITL"
(
  cd "$PX4_DIR"
  DONT_RUN=1 make "$PX4_BUILD_TARGET" "$PX4_SIM_TARGET"
)

echo "[bootstrap] Building catkin workspace"
(
  cd "$CATKIN_WS"
  catkin config --extend /opt/ros/noetic
  catkin build
)

echo
echo "[bootstrap] Done."
echo "[bootstrap] Runtime root: $INSTALL_ROOT"
echo "[bootstrap] Start simulator with: $REPO_ROOT/scripts/run_sim.sh \"$INSTALL_ROOT\""
echo "[bootstrap] Start mission with:   $REPO_ROOT/scripts/run_mission.sh \"$INSTALL_ROOT\""
