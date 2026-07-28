#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set +u
source /opt/ros/humble/setup.bash
set -u
export PATH="/usr/bin:$PATH"

"$project_root/tests/test_workspace_layout.sh"

python3 -m unittest discover -s "$project_root/tests/unit" -p "test_*.py"
python3 -m pytest "$project_root/tests/contract"

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
launch_test "$project_root/tests/launch/test_cmd_vel_guard.launch.py"
launch_test "$project_root/tests/launch/test_sim_base_motion.launch.py"
launch_test "$project_root/tests/launch/test_sim_sensors.launch.py"
launch_test "$project_root/tests/launch/test_s1_m4_motion_safety_integration.launch.py"
launch_test "$project_root/tests/launch/test_s1_m4_sensor_processing.launch.py"
launch_test "$project_root/tests/launch/test_s1_m4_ekf_fusion.launch.py"
launch_test "$project_root/tests/launch/test_s1_m5_slam.launch.py"
launch_test "$project_root/tests/launch/test_s1_m5_localization.launch.py"
launch_test "$project_root/tests/launch/test_s1_m5_nav2.launch.py"
launch_test "$project_root/tests/launch/test_s1_m5_scan_timeout.launch.py"
launch_test "$project_root/tests/launch/test_s1_m5_temporary_obstacle.launch.py"
launch_test "$project_root/tests/launch/test_s1_m6_task_manager.launch.py"
launch_test "$project_root/tests/launch/test_s1_m6_end_to_end.launch.py"
