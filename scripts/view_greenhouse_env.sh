#!/usr/bin/env bash
# Static environment only. No robot, ROS, Nav2 or motion commands.
set -euo pipefail
: "${GAZEBO_RESOURCE_PATH:=}"
: "${GAZEBO_PLUGIN_PATH:=}"
: "${LD_LIBRARY_PATH:=}"
: "${GAZEBO_MODEL_PATH:=}"
root_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source /usr/share/gazebo-11/setup.sh
export GAZEBO_IP=127.0.0.1
export GAZEBO_MODEL_DATABASE_URI=""
export GAZEBO_MODEL_PATH="$root_dir/src/ai_robot_sim/models${GAZEBO_MODEL_PATH:+:$GAZEBO_MODEL_PATH}"
export GAZEBO_MASTER_URI="${GREENHOUSE_MASTER_URI:-http://127.0.0.1:11365}"
exec gazebo --verbose "$root_dir/src/ai_robot_sim/worlds/greenhouse_env.world"
