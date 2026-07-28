#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set +u
source /opt/ros/humble/setup.bash
set -u
export PATH="/usr/bin:$PATH"

"$project_root/tests/test_workspace_layout.sh"

python3 -m unittest "$project_root/tests/unit/test_python_example.py"
python3 -m pytest "$project_root/tests/contract/test_interface_baseline.py"

colcon --log-base "$project_root/log" test \
  --base-paths "$project_root/src" \
  --build-base "$project_root/build" \
  --install-base "$project_root/install"

colcon test-result --all --test-result-base "$project_root/build"

set +u
source "$project_root/install/setup.bash"
set -u
export PATH="/usr/bin:$PATH"
launch_test "$project_root/tests/launch/test_minimal_nodes.launch.py"
