#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${workspace_dir}"
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
set -u

model_file="${1:-$(ros2 pkg prefix ai_robot_description)/share/ai_robot_description/urdf/small_yellow_car_v1.2.urdf.xacro}"
rviz_config="${workspace_dir}/config/rviz2/small_yellow_car.rviz"

if [[ ! -f "${model_file}" ]]; then
  echo "FAIL: Xacro file not found: ${model_file}" >&2
  exit 1
fi
if [[ ! -f "${rviz_config}" ]]; then
  echo "FAIL: RViz2 config not found: ${rviz_config}" >&2
  exit 1
fi
if [[ -z "${DISPLAY:-}" ]]; then
  echo "FAIL: DISPLAY is not set; run this script from a graphical desktop." >&2
  exit 1
fi

robot_description="$(xacro "${model_file}")"
rsp_pid=""
jsp_pid=""
rviz_pid=""
cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  for pid in "${rviz_pid}" "${jsp_pid}" "${rsp_pid}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      kill -TERM -- "-${pid}" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
  exit "${exit_code}"
}
trap cleanup EXIT INT TERM

setsid ros2 run robot_state_publisher robot_state_publisher \
  --ros-args -p "robot_description:=${robot_description}" \
  >/tmp/small_yellow_car_robot_state_publisher.log 2>&1 &
rsp_pid=$!
setsid ros2 run joint_state_publisher joint_state_publisher \
  --ros-args -p "robot_description:=${robot_description}" \
  >/tmp/small_yellow_car_joint_state_publisher.log 2>&1 &
jsp_pid=$!
echo "Starting RViz2 with ${model_file}"
setsid rviz2 -d "${rviz_config}" &
rviz_pid=$!
wait "${rviz_pid}"
