#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_ROOT="${1:-${INSTALL_ROOT:-$HOME/uav-usv-experiment-platform-runtime}}"

PX4_DIR="${PX4_DIR:-$INSTALL_ROOT/PX4_Firmware}"
XTDRONE_DIR="${XTDRONE_DIR:-$INSTALL_ROOT/XTDrone}"

if [[ ! -d "$PX4_DIR" ]]; then
  echo "Missing PX4 target directory: $PX4_DIR" >&2
  exit 1
fi

if [[ ! -d "$XTDRONE_DIR" ]]; then
  echo "Missing XTDrone target directory: $XTDRONE_DIR" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "Missing required command: rsync" >&2
  exit 1
fi

legacy_px4_paths=(
  "Tools/flightgear_bridge"
  "Tools/jMAVSim"
  "Tools/jsbsim_bridge"
  "Tools/simulation-ignition"
  "Tools/sitl_gazebo"
  "boards/px4/sitl/default.px4board"
  "ROMFS/px4fmu_common/init.d-posix/airframes/10016_iris.post"
  "ROMFS/px4fmu_common/init.d-posix/airframes/CMakeLists.txt"
  "ROMFS/px4fmu_common/init.d-posix/px4-rc.rtps"
  "src/drivers/uavcan_v1"
  "src/modules/microdds_client"
  "src/modules/micrortps_bridge"
  "src/modules/microdds_client/CMakeLists.txt"
  "src/modules/microdds_client/microdds_client.h"
  "src/modules/micrortps_bridge/micrortps_client/dds_topics.h"
  "src/modules/micrortps_bridge/micrortps_client/utilities.hpp"
)

for rel_path in "${legacy_px4_paths[@]}"; do
  if git -C "$PX4_DIR" ls-files --error-unmatch "$rel_path" >/dev/null 2>&1; then
    continue
  fi

  rm -rf "$PX4_DIR/$rel_path"
done

echo "[apply_overlay] Syncing PX4 overlay into $PX4_DIR"
rsync -a "$REPO_ROOT/overlays/PX4_Firmware/" "$PX4_DIR/"
if [[ -f "$PX4_DIR/scripts/px4" ]]; then
  chmod +x "$PX4_DIR/scripts/px4"
fi

echo "[apply_overlay] Syncing XTDrone overlay into $XTDRONE_DIR"
rsync -a "$REPO_ROOT/overlays/XTDrone/" "$XTDRONE_DIR/"

CATVEHICLE_SRC_DIR="$XTDRONE_DIR/sitl_config/ugv/catvehicle/src"
for rel_path in cmdvel2gazebo.py odom2path.py; do
  target="$CATVEHICLE_SRC_DIR/$rel_path"
  if [[ -f "$target" ]]; then
    sed -i '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' "$target"
  fi
done

PX4_GAZEBO_MODELS_DIR="$PX4_DIR/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models"
XTDRONE_MODELS_DIR="$XTDRONE_DIR/sitl_config/models"
if [[ -d "$PX4_GAZEBO_MODELS_DIR" && -d "$XTDRONE_MODELS_DIR" ]]; then
  echo "[apply_overlay] Syncing XTDrone Gazebo models into PX4 SITL Gazebo model tree"
  rsync -a "$XTDRONE_MODELS_DIR/" "$PX4_GAZEBO_MODELS_DIR/"
fi

echo "[apply_overlay] Done."
