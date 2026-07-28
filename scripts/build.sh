#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set +u
source /opt/ros/humble/setup.bash
set -u
export PATH="/usr/bin:$PATH"

colcon --log-base "$project_root/log" build \
  --base-paths "$project_root/src" \
  --build-base "$project_root/build" \
  --install-base "$project_root/install"
