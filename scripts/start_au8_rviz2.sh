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
if pgrep -x rviz2 >/dev/null; then
  echo "FAIL: RViz2 is already running. Stop the existing RViz2 session first." >&2
  exit 1
fi

cd "${workspace_dir}"
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
set -u

rviz_config="${workspace_dir}/config/rviz2/small_yellow_car.rviz"
if [[ ! -f "${rviz_config}" ]]; then
  echo "FAIL: RViz2 config not found: ${rviz_config}" >&2
  exit 1
fi

echo "Starting AU8 RViz2 with simulation time."
echo "Leave this terminal running while Gazebo is stopped and restarted."
exec rviz2 -d "${rviz_config}" --ros-args -p use_sim_time:=true
