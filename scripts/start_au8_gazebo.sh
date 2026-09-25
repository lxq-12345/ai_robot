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
if pgrep -x gzserver >/dev/null || pgrep -x gzclient >/dev/null; then
  echo "FAIL: Gazebo is already running. Stop the existing Gazebo session first." >&2
  exit 1
fi

cd "${workspace_dir}"
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
set -u

log_dir="${workspace_dir}/log/manual"
mkdir -p "${log_dir}"
timestamp="$(date '+%Y%m%d_%H%M%S')"
gazebo_log="${log_dir}/au8_gazebo_${timestamp}.log"
bringup_pid=""

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if [[ -n "${bringup_pid}" ]]; then
    kill -TERM -- "-${bringup_pid}" 2>/dev/null || true
    for _ in {1..40}; do
      if ! kill -0 -- "-${bringup_pid}" 2>/dev/null; then
        break
      fi
      sleep 0.25
    done
    kill -KILL -- "-${bringup_pid}" 2>/dev/null || true
    wait "${bringup_pid}" 2>/dev/null || true
    # Gazebo children can outlive the launch leader briefly; recheck the same group only.
    for _ in {1..12}; do
      if ! kill -0 -- "-${bringup_pid}" 2>/dev/null; then
        break
      fi
      kill -KILL -- "-${bringup_pid}" 2>/dev/null || true
      sleep 0.25
    done
  fi
  if pgrep -x gzserver >/dev/null || pgrep -x gzclient >/dev/null; then
    echo "WARN: an AU8 Gazebo process may remain; inspect it before restarting." >&2
    exit 1
  fi
  exit "${exit_code}"
}
trap cleanup EXIT INT TERM

echo "Starting AU8 Gazebo with apartment_v1.3 and the small yellow car..."
echo "Gazebo log: ${gazebo_log}"
setsid ros2 launch ai_robot_sim apartment_house_bringup.launch.py gui:=true \
  >"${gazebo_log}" 2>&1 &
bringup_pid=$!

deadline=$((SECONDS + 45))
ready=false
while (( SECONDS < deadline )); do
  if ! kill -0 "${bringup_pid}" 2>/dev/null; then
    echo "FAIL: Gazebo launch exited during startup." >&2
    tail -80 "${gazebo_log}" >&2
    exit 1
  fi
  if pgrep -x gzclient >/dev/null \
      && ros2 topic list 2>/dev/null | grep -Fxq /camera/image_raw \
      && ros2 topic list 2>/dev/null | grep -Fxq /camera/right/image_raw; then
    ready=true
    echo "PASS: AU8 Gazebo and both camera topics are ready."
    echo "Leave this terminal running. Press Ctrl+C to stop Gazebo independently."
    break
  fi
  sleep 1
done

if [[ "${ready}" != true ]]; then
  echo "FAIL: Gazebo GUI and both camera topics were not ready within 45 seconds." >&2
  tail -80 "${gazebo_log}" >&2
  exit 1
fi

while kill -0 "${bringup_pid}" 2>/dev/null && pgrep -x gzclient >/dev/null; do
  sleep 1
done
echo "Gazebo closed; cleaning up only the AU8 Gazebo process group."
