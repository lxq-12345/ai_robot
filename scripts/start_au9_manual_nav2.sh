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

# Give the backend its own process group. Ctrl+C is handled here so clients
# close before Launch tears down ROS/Gazebo, rather than all at once.
cleanup_started=0
cleanup() {
  local exit_status=$?
  ((cleanup_started == 0)) || return
  cleanup_started=1
  trap - EXIT
  trap '' INT TERM
  if ! bash "${workspace_dir}/scripts/stop_au9_manual_nav2.sh"; then
    echo 'ERROR: AU9 did not shut down gracefully.' >&2
    exit_status=1
  fi
  exit "$exit_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# Bash background jobs inherit SIGINT ignored. Reset it explicitly before
# exec; setsid alone changes the session, not the signal disposition.
/usr/bin/python3 -c '
import json
import os
from pathlib import Path
import signal
import sys
signal.signal(signal.SIGINT, signal.SIG_DFL)
signal.signal(signal.SIGTERM, signal.SIG_DFL)
os.setsid()
workspace = Path.cwd()
stat = Path("/proc/self/stat").read_text()
fields = stat[stat.rindex(")") + 2:].split()
record = {"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
          "root_pid": os.getpid(), "root_started": fields[19],
          "session": os.getsid(0), "owned": []}
state = workspace / "log/au9_session.json"
state.parent.mkdir(exist_ok=True)
temporary = state.with_suffix(".tmp")
temporary.write_text(json.dumps(record))
temporary.replace(state)
os.execvp(sys.argv[1], sys.argv[1:])
' ros2 launch ai_robot_sim apartment_nav2_bringup.launch.py gui:=true rviz:=true &
wait "$!"
