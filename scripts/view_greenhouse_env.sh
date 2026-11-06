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
grid_plugin_src="$root_dir/src/ai_robot_sim/plugins/greenhouse_grid_plugin.cc"
grid_plugin="$root_dir/build/greenhouse_grid/libgreenhouse_grid_plugin.so"
mkdir -p "${grid_plugin%/*}"
if [[ ! -f "$grid_plugin" || "$grid_plugin_src" -nt "$grid_plugin" ]]; then
  g++ -std=c++17 -fPIC -shared "$grid_plugin_src" -o "$grid_plugin" \
    $(pkg-config --cflags Qt5Widgets OGRE OGRE-Paging OGRE-Terrain OGRE-Overlay gazebo) \
    $(pkg-config --libs Qt5Widgets gazebo)
fi
exec gazebo --verbose --gui-client-plugin "$grid_plugin" \
  "$root_dir/src/ai_robot_sim/worlds/greenhouse_env.world"
