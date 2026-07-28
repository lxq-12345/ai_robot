#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set +u
source /opt/ros/humble/setup.bash
set -u

"$project_root/tests/test_workspace_layout.sh"

colcon --log-base "$project_root/log" test \
  --base-paths "$project_root/src" \
  --build-base "$project_root/build" \
  --install-base "$project_root/install"

colcon test-result --all --test-result-base "$project_root/build"
