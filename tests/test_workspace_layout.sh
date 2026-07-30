#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for path in README.md AGENTS.md skills/会话管理协议.md plan mem learning learning/README.md learning/ROS2仿真机器人 learning/ROS2仿真机器人/README.md learning/ROS2仿真机器人/source/PU1 learning/ROS2仿真机器人/assets/PU1 learning/ROS2仿真机器人/html/PU1 learning/ROS2仿真机器人/bks/PU1 learning/ROS2仿真机器人/source/PU1/PU1-01_项目总体架构_v1.2.md learning/ROS2仿真机器人/assets/PU1/PU1-01_项目总体架构.svg learning/ROS2仿真机器人/html/PU1/PU1-01_项目总体架构_v1.2.html src config scripts tests resources tests/unit tests/launch tests/contract tests/scenario tests/evidence; do
  if [[ ! -e "$project_root/$path" ]]; then
    echo "Required project path not found: $path" >&2
    exit 1
  fi
done

if ! git -C "$project_root" check-ignore -q docs/.keep; then
  echo "docs/ must remain local-only and ignored by Git" >&2
  exit 1
fi

echo "Workspace layout check passed"
