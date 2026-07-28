#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ros_setup="/opt/ros/humble/setup.bash"

if [[ ! -f "$ros_setup" ]]; then
  echo "ROS 2 Humble setup file not found: $ros_setup" >&2
  exit 1
fi

set +u
source "$ros_setup"
set -u
export PATH="/usr/bin:$PATH"

for command in colcon ros2 rviz2 gazebo gzserver; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Required command not found: $command" >&2
    exit 1
  fi
done

for directory in src config scripts tests resources; do
  if [[ ! -d "$project_root/$directory" ]]; then
    echo "Required workspace directory not found: $directory" >&2
    exit 1
  fi
done

echo "ROS_DISTRO=$ROS_DISTRO"
echo "Workspace baseline check passed: $project_root"
