#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if (( $# != 0 )); then
  echo "Usage: $0" >&2
  exit 2
fi

if [[ -z "${DISPLAY:-}" ]]; then
  echo "FAIL: DISPLAY is not set; run this test from the graphical desktop." >&2
  exit 1
fi

if pgrep -x gzserver >/dev/null || pgrep -x gzclient >/dev/null; then
  echo "FAIL: Gazebo is already running. Stop it before this isolated GUI test." >&2
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
run_log="${log_dir}/apartment_house_gui_${timestamp}.log"

bringup_pid=""
cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if [[ -n "${bringup_pid}" ]] && kill -0 "${bringup_pid}" 2>/dev/null; then
    kill -TERM -- "-${bringup_pid}" 2>/dev/null || true
    for _ in {1..20}; do
      if ! kill -0 "${bringup_pid}" 2>/dev/null; then
        break
      fi
      sleep 0.25
    done
    if kill -0 -- "-${bringup_pid}" 2>/dev/null; then
      kill -KILL -- "-${bringup_pid}" 2>/dev/null || true
    fi
    wait "${bringup_pid}" 2>/dev/null || true
  fi
  for _ in {1..20}; do
    if ! pgrep -x gzserver >/dev/null && ! pgrep -x gzclient >/dev/null; then
      break
    fi
    sleep 0.25
  done
  if pgrep -x gzserver >/dev/null || pgrep -x gzclient >/dev/null; then
    echo "WARN: a Gazebo process remains; inspect it before another test." >&2
    exit 1
  fi
  exit "${exit_code}"
}
trap cleanup EXIT INT TERM

echo "Starting apartment-house Gazebo GUI..."
echo "Run log: ${run_log}"
setsid ros2 launch ai_robot_sim apartment_house_bringup.launch.py gui:=true \
  >"${run_log}" 2>&1 &
bringup_pid=$!

deadline=$((SECONDS + 45))
while (( SECONDS < deadline )); do
  if ! kill -0 "${bringup_pid}" 2>/dev/null; then
    echo "FAIL: ROS launch exited before Gazebo became ready." >&2
    tail -80 "${run_log}" >&2
    exit 1
  fi
  if pgrep -x gzclient >/dev/null \
      && ros2 service list 2>/dev/null | grep -qx '/get_model_list' \
      && ros2 topic list 2>/dev/null | grep -qx '/scan' \
      && ros2 topic list 2>/dev/null | grep -qx '/odom'; then
    break
  fi
  sleep 1
done

if ! pgrep -x gzclient >/dev/null; then
  echo "FAIL: Gazebo graphical client did not start within 45 seconds." >&2
  tail -80 "${run_log}" >&2
  exit 1
fi

model_output="$(
  timeout 12 ros2 service call /get_model_list gazebo_msgs/srv/GetModelList '{}' 2>&1
)"
for model_name in apartment_house ground ai_robot; do
  if [[ "${model_output}" != *"'${model_name}'"* ]]; then
    echo "FAIL: model '${model_name}' is missing from Gazebo." >&2
    echo "${model_output}" >&2
    exit 1
  fi
done

scan_output="$(timeout 12 ros2 topic echo /scan --once --field header 2>&1)"
odom_output="$(timeout 12 ros2 topic echo /odom --once --field header 2>&1)"
if [[ "${scan_output}" != *"frame_id: laser_link"* ]]; then
  echo "FAIL: /scan did not publish with frame laser_link." >&2
  exit 1
fi
if [[ "${odom_output}" != *"frame_id: odom"* ]]; then
  echo "FAIL: /odom did not publish with frame odom." >&2
  exit 1
fi

pose_output="$(timeout 12 gz model -m ai_robot -p 2>&1)"
read -r pose_x pose_y pose_z _ <<<"${pose_output}"
if ! awk -v x="${pose_x}" -v y="${pose_y}" \
  'BEGIN { exit !(x >= 1.75 && x <= 1.85 && y >= 3.95 && y <= 4.05) }'; then
  echo "FAIL: robot pose is outside the expected spawn tolerance: ${pose_output}" >&2
  exit 1
fi

echo "PASS: gzclient is running on DISPLAY=${DISPLAY}."
echo "PASS: apartment_house, ground and ai_robot are loaded."
echo "PASS: robot pose is ${pose_x}, ${pose_y}, ${pose_z}."
echo "PASS: /scan uses laser_link and /odom uses odom."
echo ""
echo "Observe the GUI now:"
echo "  1. The two-bedroom apartment walls, openings and east windows are visible."
echo "  2. The yellow four-wheel robot is inside the house near (1.80, 4.00)."
echo "  3. The robot is stable and does not overlap a wall or fall through the floor."
echo "  4. Press Esc, then use middle-button drag or Shift+left-button drag to orbit."
echo "     Use left-button drag to pan and the wheel or right-button drag to zoom."
echo "The window will remain open until you press Ctrl+C or close Gazebo."
echo "Automated GUI/runtime checks passed; visual acceptance still requires operator evidence."

while kill -0 "${bringup_pid}" 2>/dev/null && pgrep -x gzclient >/dev/null; do
  sleep 1
done
echo "Gazebo GUI closed; cleaning up this test run."
