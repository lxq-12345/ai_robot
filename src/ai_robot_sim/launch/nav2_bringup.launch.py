from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import SetRemap


def generate_launch_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    nav2_share = get_package_share_directory("nav2_bringup")
    gui = LaunchConfiguration("gui")
    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="false",
        description="Start the Gazebo graphical client.",
    )
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{sim_share}/launch/localization_bringup.launch.py"
        ),
        launch_arguments={"gui": gui, "require_scan": "true"}.items(),
    )
    navigation = GroupAction(
        [
            # Nav2's final velocity output remains subject to the project safety guard.
            SetRemap(src="/cmd_vel", dst="/cmd_vel_raw"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(f"{nav2_share}/launch/navigation_launch.py"),
                launch_arguments={
                    "use_sim_time": "true",
                    "use_composition": "False",
                    "params_file": f"{nav2_share}/params/nav2_params.yaml",
                }.items(),
            ),
        ]
    )
    # Gazebo must first spawn the base and publish odom -> base_footprint for costmaps.
    return LaunchDescription(
        [gui_arg, localization, TimerAction(period=8.0, actions=[navigation])]
    )
