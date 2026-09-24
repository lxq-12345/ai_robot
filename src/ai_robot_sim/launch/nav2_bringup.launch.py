from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap


def generate_launch_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    gui = LaunchConfiguration("gui")
    rviz = LaunchConfiguration("rviz")
    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="false",
        description="Start the Gazebo graphical client.",
    )
    rviz_arg = DeclareLaunchArgument(
        "rviz",
        default_value="false",
        description="Start RViz2 after the localization frame is available.",
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
                PythonLaunchDescriptionSource(
                    f"{get_package_share_directory('nav2_bringup')}/launch/navigation_launch.py"
                ),
                launch_arguments={
                    "use_sim_time": "true",
                    "use_composition": "False",
                    "params_file": f"{sim_share}/config/nav2_sim.yaml",
                }.items(),
            ),
        ]
    )
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz",
        arguments=[
            "-d",
            f"{get_package_share_directory('nav2_bringup')}/rviz/nav2_default_view.rviz",
        ],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(rviz),
        output="screen",
    )
    # Gazebo must first spawn the base and publish odom -> base_footprint for costmaps.
    return LaunchDescription(
        [
            gui_arg,
            rviz_arg,
            localization,
            TimerAction(period=8.0, actions=[navigation]),
            TimerAction(period=10.0, actions=[rviz_node]),
        ]
    )
