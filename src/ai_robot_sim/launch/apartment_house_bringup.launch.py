from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    description_share = get_package_share_directory("ai_robot_description")
    sim_share = get_package_share_directory("ai_robot_sim")
    gui = LaunchConfiguration("gui")
    require_scan = LaunchConfiguration("require_scan")
    command_input_topic = LaunchConfiguration("command_input_topic")
    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="true",
        description="Start Gazebo Classic with the apartment graphical view.",
    )
    require_scan_arg = DeclareLaunchArgument(
        "require_scan",
        default_value="false",
        description="Require fresh laser scans in the velocity safety guard.",
    )
    command_input_topic_arg = DeclareLaunchArgument(
        "command_input_topic",
        default_value="/cmd_vel_raw",
        description="Velocity topic consumed by the safety guard.",
    )
    bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(f"{sim_share}/launch/sim_bringup.launch.py"),
        launch_arguments={
            "gui": gui,
            "require_scan": require_scan,
            "command_input_topic": command_input_topic,
            "command_output_topic": "/cmd_vel_safe",
            "world": f"{sim_share}/worlds/apartment_v1.3.world",
            "spawn_x": "1.80",
            "spawn_y": "4.00",
            "spawn_z": "0.10",
            "robot_model": f"{description_share}/urdf/small_yellow_car_v1.2.urdf.xacro",
            "robot_sdf": f"{description_share}/models/small_yellow_car_v1.2.sdf",
            "spawn_from_sdf": "true",
        }.items(),
    )
    return LaunchDescription(
        [gui_arg, require_scan_arg, command_input_topic_arg, bringup]
    )
