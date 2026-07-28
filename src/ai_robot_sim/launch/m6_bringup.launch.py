from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    gui = LaunchConfiguration("gui")
    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="false",
        description="Start the Gazebo graphical client.",
    )
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{sim_share}/launch/nav2_bringup.launch.py"
        ),
        launch_arguments={"gui": gui}.items(),
    )
    task_manager = Node(
        package="ai_robot_sim",
        executable="capability_task_manager",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )
    return LaunchDescription([gui_arg, nav2, task_manager])
