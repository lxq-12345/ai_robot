#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for path in README.md AGENTS.md skills/会话管理协议.md plan mem learning learning/README.md learning/ROS2仿真机器人 learning/ROS2仿真机器人/README.md learning/ROS2仿真机器人/source/S1-1-M0 learning/ROS2仿真机器人/assets/S1-1-M0 learning/ROS2仿真机器人/html/S1-1-M0 learning/ROS2仿真机器人/source/S1-1-M1 learning/ROS2仿真机器人/assets/S1-1-M1 learning/ROS2仿真机器人/html/S1-1-M1 learning/ROS2仿真机器人/bks/PU1 learning/ROS2仿真机器人/source/S1-1-M0/S1-1-M0-L1-01_项目总体架构_v1.6.md learning/ROS2仿真机器人/assets/S1-1-M0/S1-1-M0-L1-01_项目总体架构.svg learning/ROS2仿真机器人/html/S1-1-M0/S1-1-M0-L1-01_项目总体架构_v1.6.html learning/ROS2仿真机器人/source/S1-1-M0/S1-1-M0-L1-02_工作空间与目录_v1.4.md learning/ROS2仿真机器人/assets/S1-1-M0/S1-1-M0-L1-02_工作空间与目录.svg learning/ROS2仿真机器人/html/S1-1-M0/S1-1-M0-L1-02_工作空间与目录_v1.4.html learning/ROS2仿真机器人/source/S1-1-M0/S1-1-M0-L2-01_环境构建运行与项目管理_v1.0.md learning/ROS2仿真机器人/html/S1-1-M0/S1-1-M0-L2-01_环境构建运行与项目管理_v1.0.html learning/ROS2仿真机器人/source/S1-1-M1/S1-1-M1-L1-01_程序包与工程资源_v1.2.md learning/ROS2仿真机器人/assets/S1-1-M1/S1-1-M1-L1-01_程序包与工程资源.svg learning/ROS2仿真机器人/html/S1-1-M1/S1-1-M1-L1-01_程序包与工程资源_v1.2.html learning/ROS2仿真机器人/source/S1-1-M1/S1-1-M1-L2-01_对象与链路概览_v1.1.md learning/ROS2仿真机器人/assets/S1-1-M1/S1-1-M1-L2-01_对象与链路概览.svg learning/ROS2仿真机器人/html/S1-1-M1/S1-1-M1-L2-01_对象与链路概览_v1.1.html learning/ROS2仿真机器人/source/S1-1-M1/S1-1-M1-L3-01_实体迁移概览_v1.4.md learning/ROS2仿真机器人/assets/S1-1-M1/S1-1-M1-L3-01_实体迁移概览.svg learning/ROS2仿真机器人/html/S1-1-M1/S1-1-M1-L3-01_实体迁移概览_v1.4.html src config scripts tests resources tests/README.md tests/contract tests/integration tests/system tests/helpers tests/scenario tests/evidence src/ai_robot_sim/test src/ai_robot_py_example/test; do
  if [[ ! -e "$project_root/$path" ]]; then
    echo "Required project path not found: $path" >&2
    exit 1
  fi
done

for obsolete_path in tests/unit tests/launch; do
  if [[ -e "$project_root/$obsolete_path" ]]; then
    echo "Obsolete test directory must not exist: $obsolete_path" >&2
    exit 1
  fi
done

if ! git -C "$project_root" check-ignore -q docs/.keep; then
  echo "docs/ must remain local-only and ignored by Git" >&2
  exit 1
fi

echo "Workspace layout check passed"
