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

echo "[apply_overlay] Syncing PX4 overlay into $PX4_DIR"
rsync -a "$REPO_ROOT/overlays/PX4_Firmware/" "$PX4_DIR/"

echo "[apply_overlay] Syncing XTDrone overlay into $XTDRONE_DIR"
rsync -a "$REPO_ROOT/overlays/XTDrone/" "$XTDRONE_DIR/"

echo "[apply_overlay] Done."
