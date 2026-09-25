#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if (( $# != 0 )); then
  echo "Usage: $0" >&2
  exit 2
fi

cd "${workspace_dir}"
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
set -u

if ! pgrep -x gzserver >/dev/null || ! pgrep -x gzclient >/dev/null; then
  echo "FAIL: AU8 Gazebo is not running. Start scripts/start_au8_gazebo.sh first." >&2
  exit 1
fi
if ! pgrep -x rviz2 >/dev/null; then
  echo "FAIL: AU8 RViz2 is not running. Start scripts/start_au8_rviz2.sh first." >&2
  exit 1
fi

log_dir="${workspace_dir}/log/manual"
mkdir -p "${log_dir}"
timestamp="$(date '+%Y%m%d_%H%M%S')"
qos_log="${log_dir}/au8_camera_qos_${timestamp}.log"

wait_for_topic() {
  local topic="$1"
  local deadline=$((SECONDS + 20))
  while (( SECONDS < deadline )); do
    if ros2 topic list 2>/dev/null | grep -Fxq "${topic}"; then
      return 0
    fi
    sleep 1
  done
  echo "FAIL: topic ${topic} was not available within 20 seconds." >&2
  return 1
}

check_header_frame() {
  local topic="$1"
  local expected_frame="$2"
  local output
  output="$(timeout 12 ros2 topic echo "${topic}" --once --field header 2>&1)"
  if [[ "${output}" != *"frame_id: ${expected_frame}"* ]]; then
    echo "FAIL: ${topic} did not use frame ${expected_frame}." >&2
    echo "${output}" >&2
    return 1
  fi
}

check_rate() {
  local topic="$1"
  local output average
  output="$(timeout 6 ros2 topic hz "${topic}" --window 20 2>&1 || true)"
  average="$(sed -n 's/.*average rate: \([0-9.]*\).*/\1/p' <<<"${output}" | tail -1)"
  if [[ -z "${average}" ]] || ! awk -v rate="${average}" 'BEGIN { exit !(rate >= 7.0 && rate <= 13.0) }'; then
    echo "FAIL: ${topic} did not demonstrate the expected 10 Hz camera rate." >&2
    echo "${output}" >&2
    return 1
  fi
  echo "PASS: ${topic} average rate is ${average} Hz."
}

for topic in \
  /clock \
  /scan \
  /camera/image_raw \
  /camera/camera_info \
  /camera/right/image_raw \
  /camera/right/camera_info; do
  wait_for_topic "${topic}"
done

check_header_frame /camera/image_raw camera_left_optical_frame
check_header_frame /camera/camera_info camera_left_optical_frame
check_header_frame /camera/right/image_raw camera_right_optical_frame
check_header_frame /camera/right/camera_info camera_right_optical_frame

left_info="$(timeout 12 ros2 topic echo /camera/camera_info --once 2>&1)"
right_info="$(timeout 12 ros2 topic echo /camera/right/camera_info --once 2>&1)"
for value in "width: 640" "height: 480"; do
  if [[ "${left_info}" != *"${value}"* ]] || [[ "${right_info}" != *"${value}"* ]]; then
    echo "FAIL: CameraInfo is missing expected ${value}." >&2
    exit 1
  fi
done

for frame in camera_left_optical_frame camera_right_optical_frame; do
  tf_output="$(timeout 8 ros2 run tf2_ros tf2_echo base_link "${frame}" 2>&1 || true)"
  if [[ "${tf_output}" != *"Translation:"* ]]; then
    echo "FAIL: TF base_link -> ${frame} was not available." >&2
    echo "${tf_output}" >&2
    exit 1
  fi
done

check_rate /camera/image_raw
check_rate /camera/right/image_raw

rviz_node="$(ros2 node list 2>/dev/null | grep -E '^/rviz2?$' | head -1 || true)"
if [[ -z "${rviz_node}" ]]; then
  echo "FAIL: RViz2 node was not discovered." >&2
  exit 1
fi
rviz_time="$(ros2 param get "${rviz_node}" use_sim_time 2>&1)"
if [[ "${rviz_time}" != *"True"* ]]; then
  echo "FAIL: ${rviz_node} is not using simulation time." >&2
  echo "${rviz_time}" >&2
  exit 1
fi

{
  echo "# /camera/image_raw"
  ros2 topic info /camera/image_raw -v
  echo "# /camera/right/image_raw"
  ros2 topic info /camera/right/image_raw -v
} >"${qos_log}"
for topic in /camera/image_raw /camera/right/image_raw; do
  topic_summary="$(ros2 topic info "${topic}" 2>&1)"
  if [[ "${topic_summary}" == *"Subscription count: 0"* ]]; then
    echo "FAIL: RViz2 did not subscribe to ${topic}." >&2
    echo "${topic_summary}" >&2
    exit 1
  fi
done

echo "PASS: AU8 Gazebo and RViz2 are independently running."
echo "PASS: left/right Image and CameraInfo topics publish with optical frames."
echo "PASS: both camera rates are within 7-13 Hz and camera TF is connected."
echo "PASS: RViz2 uses simulation time and subscribes to both image topics."
echo "QoS evidence: ${qos_log}"
