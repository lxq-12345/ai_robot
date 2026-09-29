#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if (( $# != 0 )); then
  echo "Usage: $0" >&2
  exit 2
fi
if [[ -z "${DISPLAY:-}" ]]; then
  echo "FAIL: DISPLAY is not set; run this script from the graphical desktop." >&2
  exit 1
fi

for process_name in gzserver gzclient rviz2; do
  if pgrep -x "${process_name}" >/dev/null; then
    echo "FAIL: ${process_name} is already running. Stop the existing simulation first." >&2
    exit 1
  fi
done

cd "${workspace_dir}"
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
set -u

echo "Starting the AU9 manual Nav2 test in Gazebo and RViz2."
echo "Wait for the map and laser scan, then use 'Nav2 Goal' in RViz2."
echo "Safe first targets: (2.20, 4.00), then (2.60, 4.00)."
echo "Press Ctrl+C in this terminal to stop the complete test environment."

exec ros2 launch ai_robot_sim apartment_nav2_bringup.launch.py gui:=true rviz:=true
