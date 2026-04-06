#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_ROOT="${1:-${INSTALL_ROOT:-$HOME/uav-landing-experiment-platform-runtime}}"

CATKIN_WS="${CATKIN_WS:-$INSTALL_ROOT/catkin_ws}"
PX4_DIR="${PX4_DIR:-$INSTALL_ROOT/PX4_Firmware}"
ROS2_PX4_WS="${ROS2_PX4_WS:-$INSTALL_ROOT/ros2_px4_ws}"
ROS2_RESEARCH_WS="${ROS2_RESEARCH_WS:-$INSTALL_ROOT/ros2_research_ws}"
ROS1_BRIDGE_WS="${ROS1_BRIDGE_WS:-$INSTALL_ROOT/ros1_bridge_ws}"
# Pinned from the validated PX4 ROS 2 release branches to keep fresh-machine bootstrap reproducible.
PX4_MSGS_REF="${PX4_MSGS_REF:-ffb6e80e1c17e5714395611a020c282a87af8fa4}"
PX4_ROS_COM_REF="${PX4_ROS_COM_REF:-e18248db6211350e6a418cb08ae38f64c314a2f4}"
ROS1_BRIDGE_REPO_URL="${ROS1_BRIDGE_REPO_URL:-https://github.com/ros2/ros1_bridge.git}"
ROS1_BRIDGE_REF="${ROS1_BRIDGE_REF:-foxy}"
USE_PX4_UPDATE_BRIDGE="${USE_PX4_UPDATE_BRIDGE:-0}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

install_runtime_scripts() {
  mkdir -p "$INSTALL_ROOT/scripts"
  rm -f "$INSTALL_ROOT/scripts/run_ros1_deck_interface.sh"
  rsync -a \
    "$REPO_ROOT/scripts/run_chain_validation.sh" \
    "$REPO_ROOT/scripts/scenario_world_profiles.sh" \
    "$REPO_ROOT/scripts/run_sim.sh" \
    "$REPO_ROOT/scripts/run_mission.sh" \
    "$REPO_ROOT/scripts/run_ros1_world.sh" \
    "$REPO_ROOT/scripts/run_ros1_platform_interface.sh" \
    "$REPO_ROOT/scripts/run_microxrce_agent.sh" \
    "$REPO_ROOT/scripts/run_ros1_bridge.sh" \
    "$REPO_ROOT/scripts/run_ros2_research.sh" \
    "$REPO_ROOT/scripts/ensure_ros1_controller_deps.sh" \
    "$REPO_ROOT/scripts/run_ugv_motion_baseline.sh" \
    "$REPO_ROOT/scripts/stop_platform.sh" \
    "$INSTALL_ROOT/scripts/"
  chmod +x "$INSTALL_ROOT/scripts/"*.sh
}

source_setup() {
  local setup_file="$1"
  set +u
  source "$setup_file"
  set -u
}

reset_ros_env() {
  unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH LD_LIBRARY_PATH PKG_CONFIG_PATH PYTHONPATH
  unset ROS_DISTRO ROS_ETC_DIR ROS_MASTER_URI ROS_PACKAGE_PATH ROS_ROOT ROS_VERSION ROS_PYTHON_VERSION
  unset ROS_LOCALHOST_ONLY ROSLISP_PACKAGE_DIRECTORIES ROS_DOMAIN_ID RMW_IMPLEMENTATION
}

ensure_ascii_path() {
  local path_value="$1"

  if printf '%s' "$path_value" | LC_ALL=C grep -q '[^ -~]'; then
    echo "The mixed-stack runtime path must be ASCII-only: $path_value" >&2
    echo "Use a path such as ~/uav-landing-experiment-platform-runtime." >&2
    exit 1
  fi
}

ensure_microxrce_agent() {
  if command -v MicroXRCEAgent >/dev/null 2>&1; then
    return
  fi

  echo "MicroXRCEAgent was not found in PATH." >&2
  echo "Install it before running the mixed bootstrap; see the fresh-Ubuntu prerequisites in README.md." >&2
  exit 1
}

clone_or_checkout_simple() {
  local repo_url="$1"
  local target_dir="$2"
  local repo_ref="$3"
  local label="$4"

  if [[ -d "$target_dir/.git" ]]; then
    echo "[mixed-bootstrap] Reusing existing $label at $target_dir"
    git -C "$target_dir" fetch --all --tags
  elif [[ -e "$target_dir" ]]; then
    echo "[mixed-bootstrap] Refusing to use $target_dir because it exists and is not a git repository" >&2
    exit 1
  else
    echo "[mixed-bootstrap] Cloning $label from $repo_url"
    git clone "$repo_url" "$target_dir"
  fi

  echo "[mixed-bootstrap] Checking out $label ref $repo_ref"
  git -C "$target_dir" checkout "$repo_ref"
}

clean_stale_ros2_research_artifacts() {
  local workspace_root="$1"
  local stale_packages=(
    "uav_usv_landing_msgs"
    "deck_interface"
  )

  for package_name in "${stale_packages[@]}"; do
    rm -rf \
      "$workspace_root/build/$package_name" \
      "$workspace_root/install/$package_name"
  done
}

if [[ ! -f /opt/ros/noetic/setup.bash ]]; then
  echo "ROS Noetic was not found at /opt/ros/noetic/setup.bash" >&2
  exit 1
fi

if [[ ! -f /opt/ros/foxy/setup.bash ]]; then
  echo "ROS 2 Foxy was not found at /opt/ros/foxy/setup.bash" >&2
  exit 1
fi

ensure_ascii_path "$INSTALL_ROOT"

need_cmd colcon
need_cmd git
need_cmd rsync
ensure_microxrce_agent

echo "[mixed-bootstrap] Building ROS 1 runtime"
"$SCRIPT_DIR/bootstrap.sh" "$INSTALL_ROOT"

echo "[mixed-bootstrap] Refreshing runtime launcher scripts"
install_runtime_scripts

mkdir -p "$ROS2_PX4_WS/src" "$ROS2_RESEARCH_WS/src" "$ROS1_BRIDGE_WS/src"

if [[ ! -d "$ROS2_PX4_WS/src/px4_msgs" || ! -d "$ROS2_PX4_WS/src/px4_ros_com" ]]; then
  need_cmd vcs
  echo "[mixed-bootstrap] Importing PX4 ROS 2 repositories"
  vcs import "$ROS2_PX4_WS/src" < "$REPO_ROOT/ros2_px4_ws.repos"
fi

if [[ -d "$ROS2_PX4_WS/src/px4_msgs/.git" ]]; then
  git -C "$ROS2_PX4_WS/src/px4_msgs" checkout "$PX4_MSGS_REF"
fi

if [[ -d "$ROS2_PX4_WS/src/px4_ros_com/.git" ]]; then
  git -C "$ROS2_PX4_WS/src/px4_ros_com" checkout "$PX4_ROS_COM_REF"
fi

clone_or_checkout_simple "$ROS1_BRIDGE_REPO_URL" "$ROS1_BRIDGE_WS/src/ros1_bridge" "$ROS1_BRIDGE_REF" "ros1_bridge"

if [[ "$USE_PX4_UPDATE_BRIDGE" == "1" && -x "$PX4_DIR/Tools/update_px4_ros2_bridge.sh" && -d "$ROS2_PX4_WS/src/px4_msgs" && -d "$ROS2_PX4_WS/src/px4_ros_com" ]]; then
  echo "[mixed-bootstrap] Syncing px4_msgs and px4_ros_com against $PX4_DIR"
  "$PX4_DIR/Tools/update_px4_ros2_bridge.sh" --ws_dir "$ROS2_PX4_WS" --all
else
  echo "[mixed-bootstrap] Skipping PX4 update_px4_ros2_bridge.sh (set USE_PX4_UPDATE_BRIDGE=1 to enable it)"
fi

echo "[mixed-bootstrap] Syncing ROS 2 research workspace snapshot"
rsync -a --delete "$REPO_ROOT/ros2_research_ws_src/" "$ROS2_RESEARCH_WS/src/"
clean_stale_ros2_research_artifacts "$ROS2_RESEARCH_WS"

if [[ -d "$ROS2_PX4_WS/src/px4_msgs" && -d "$ROS2_PX4_WS/src/px4_ros_com" ]]; then
  echo "[mixed-bootstrap] Building ros2_px4_ws"
  (
    reset_ros_env
    source_setup /opt/ros/foxy/setup.bash
    cd "$ROS2_PX4_WS"
    colcon build --symlink-install
  )
else
  echo "[mixed-bootstrap] Skipping ros2_px4_ws build because px4_msgs or px4_ros_com are missing."
fi

echo "[mixed-bootstrap] Building ros2_research_ws"
(
  reset_ros_env
  source_setup /opt/ros/foxy/setup.bash
  cd "$ROS2_RESEARCH_WS"
  if [[ -f "$ROS2_PX4_WS/install/setup.bash" ]]; then
    source_setup "$ROS2_PX4_WS/install/setup.bash"
  fi
  colcon build --symlink-install
)

echo "[mixed-bootstrap] Building ros1_bridge_ws"
(
  reset_ros_env
  source_setup /opt/ros/noetic/setup.bash
  source_setup "$CATKIN_WS/devel/setup.bash"
  source_setup /opt/ros/foxy/setup.bash
  if [[ -f "$ROS2_PX4_WS/install/setup.bash" ]]; then
    source_setup "$ROS2_PX4_WS/install/setup.bash"
  fi
  if [[ -f "$ROS2_RESEARCH_WS/install/setup.bash" ]]; then
    source_setup "$ROS2_RESEARCH_WS/install/setup.bash"
  fi
  cd "$ROS1_BRIDGE_WS"
  colcon build --symlink-install --packages-select ros1_bridge --cmake-force-configure
)

echo
echo "[mixed-bootstrap] Done."
echo "[mixed-bootstrap] Next terminals:"
echo "  1. $INSTALL_ROOT/scripts/run_ros1_world.sh --scenario scenario_3_maritime_usv_qr"
echo "  2. $INSTALL_ROOT/scripts/run_ros1_platform_interface.sh"
echo "  3. $INSTALL_ROOT/scripts/run_microxrce_agent.sh"
echo "  4. $INSTALL_ROOT/scripts/run_ros1_bridge.sh"
echo "  5. $INSTALL_ROOT/scripts/run_ros2_research.sh"
echo "  Chain validation: $INSTALL_ROOT/scripts/run_chain_validation.sh --scenario scenario_1_static_ground_qr"
