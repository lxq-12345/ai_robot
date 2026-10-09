#!/usr/bin/env bash
# Source this in every terminal used for the local AU9 simulation.
_au9_environment_workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_au9_environment_nounset=0
[[ $- == *u* ]] && _au9_environment_nounset=1
set +u
source /opt/ros/humble/setup.bash
source "${_au9_environment_workspace}/install/setup.bash"
((_au9_environment_nounset == 0)) || set -u

export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOCALHOST_ONLY=1
export FASTRTPS_DEFAULT_PROFILES_FILE="${_au9_environment_workspace}/config/fastdds/au9_udp_loopback.xml"
unset _au9_environment_workspace _au9_environment_nounset
