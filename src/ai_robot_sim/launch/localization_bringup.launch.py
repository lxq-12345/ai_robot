from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    gui = LaunchConfiguration("gui")
    require_scan = LaunchConfiguration("require_scan")
    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="false",
        description="Start the Gazebo graphical client.",
    )
    require_scan_arg = DeclareLaunchArgument(
        "require_scan",
        default_value="false",
        description="Require fresh laser scans in the base velocity safety guard.",
    )
    bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(f"{sim_share}/launch/sim_bringup.launch.py"),
        launch_arguments={
            "world": f"{sim_share}/worlds/s1_m5_navigation.world",
            "gui": gui,
            "require_scan": require_scan,
        }.items(),
    )
    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        parameters=[{"use_sim_time": True, "yaml_filename": f"{sim_share}/maps/s1_m5_navigation.yaml"}],
        output="screen",
    )
    amcl = Node(
        package="nav2_amcl",
        executable="amcl",
        parameters=[f"{sim_share}/config/amcl_sim.yaml"],
        output="screen",
    )
    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_localization",
        parameters=[{"use_sim_time": True, "autostart": True, "node_names": ["map_server", "amcl"]}],
        output="screen",
    )
    return LaunchDescription(
        [gui_arg, require_scan_arg, bringup, map_server, amcl, lifecycle_manager]
    )
