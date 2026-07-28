#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${workspace_dir}"

if [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is not set; start this test from the graphical desktop."
  exit 1
fi

set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
set -u

echo "Starting Gazebo, AMCL, Nav2 and the M6 task manager..."
ros2 launch ai_robot_sim m6_bringup.launch.py gui:=true &
bringup_pid=$!

cleanup() {
  kill -INT "${bringup_pid}" 2>/dev/null || true
  wait "${bringup_pid}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

ros2 run ai_robot_sim manual_m5_m6_experience --scenario all
