from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(f"{sim_share}/launch/sim_bringup.launch.py"),
        launch_arguments={"world": f"{sim_share}/worlds/s1_m5_navigation.world"}.items(),
    )
    slam = Node(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        parameters=[f"{sim_share}/config/slam_sim.yaml"],
        output="screen",
    )
    map_saver = Node(
        package="nav2_map_server",
        executable="map_saver_server",
        name="map_saver",
        parameters=[{"use_sim_time": True, "save_map_timeout": 5.0}],
        output="screen",
    )
    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_map_saver",
        parameters=[
            {"use_sim_time": True, "autostart": True, "node_names": ["map_saver"]}
        ],
        output="screen",
    )
    return LaunchDescription([bringup, slam, map_saver, lifecycle_manager])
