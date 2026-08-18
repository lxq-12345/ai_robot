#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set +u
source /opt/ros/humble/setup.bash
set -u
export PATH="/usr/bin:$PATH"
export ROS_LOG_DIR="$project_root/log/test"
mkdir -p "$ROS_LOG_DIR"

"$project_root/tests/test_workspace_layout.sh"

if [[ ! -f "$project_root/install/setup.bash" ]]; then
  echo "Workspace is not built; run ./scripts/build.sh before testing" >&2
  exit 1
fi

set +u
source "$project_root/install/setup.bash"
set -u
export PATH="/usr/bin:$PATH"

colcon --log-base "$project_root/log" test \
  --base-paths "$project_root/src" \
  --build-base "$project_root/build" \
  --install-base "$project_root/install"

colcon test-result --all --test-result-base "$project_root/build"

python3 -m pytest "$project_root/tests/contract"

integration_tests=(
  test_s1_m1_minimal_nodes.launch.py
  test_s1_m2_base_motion.launch.py
  test_s1_m3_sensors.launch.py
  test_s1_m4_motion_safety.launch.py
  test_s1_m4_sensor_processing.launch.py
  test_s1_m4_ekf_fusion.launch.py
  test_s1_m5_slam.launch.py
  test_s1_m5_localization.launch.py
  test_s1_m5_nav2.launch.py
  test_s1_m5_scan_timeout.launch.py
  test_s1_m5_temporary_obstacle.launch.py
  test_s1_m6_task_manager.launch.py
)

for test_file in "${integration_tests[@]}"; do
  launch_test "$project_root/tests/integration/$test_file"
done

system_tests=(
  test_s1_m6_end_to_end.launch.py
)

for test_file in "${system_tests[@]}"; do
  launch_test "$project_root/tests/system/$test_file"
done
