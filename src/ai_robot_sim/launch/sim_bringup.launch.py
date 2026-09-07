from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    description_share = get_package_share_directory("ai_robot_description")
    gazebo_share = get_package_share_directory("gazebo_ros")
    sim_share = get_package_share_directory("ai_robot_sim")
    xacro_file = f"{description_share}/urdf/ai_robot.urdf.xacro"

    gui = LaunchConfiguration("gui")
    world = LaunchConfiguration("world")
    require_scan = LaunchConfiguration("require_scan")
    spawn_x = LaunchConfiguration("spawn_x")
    spawn_y = LaunchConfiguration("spawn_y")
    spawn_z = LaunchConfiguration("spawn_z")
    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="false",
        description="Start Gazebo Classic with a graphical client when true.",
    )
    world_arg = DeclareLaunchArgument(
        "world",
        default_value=f"{gazebo_share}/worlds/empty.world",
        description="Gazebo Classic world file used by the simulation.",
    )
    require_scan_arg = DeclareLaunchArgument(
        "require_scan",
        default_value="false",
        description="Require fresh laser scans before forwarding base velocity commands.",
    )
    spawn_x_arg = DeclareLaunchArgument(
        "spawn_x",
        default_value="0.0",
        description="Robot spawn position on the Gazebo world X axis in metres.",
    )
    spawn_y_arg = DeclareLaunchArgument(
        "spawn_y",
        default_value="0.0",
        description="Robot spawn position on the Gazebo world Y axis in metres.",
    )
    spawn_z_arg = DeclareLaunchArgument(
        "spawn_z",
        default_value="0.10",
        description="Robot spawn position on the Gazebo world Z axis in metres.",
    )
    robot_description = Command([FindExecutable(name="xacro"), " ", xacro_file])
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(f"{gazebo_share}/launch/gazebo.launch.py"),
        launch_arguments={"gui": gui, "verbose": "true", "world": world}.items(),
    )
    state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description}],
        output="screen",
    )
    spawn = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=[
            "-entity",
            "ai_robot",
            "-topic",
            "robot_description",
            "-x",
            spawn_x,
            "-y",
            spawn_y,
            "-z",
            spawn_z,
        ],
        output="screen",
    )
    command_guard = Node(
        package="ai_robot_sim",
        executable="cmd_vel_guard",
        parameters=[
            f"{sim_share}/config/sim_base.yaml",
            {"require_scan": ParameterValue(require_scan, value_type=bool)},
        ],
        output="screen",
    )
    return LaunchDescription(
        [
            gui_arg,
            world_arg,
            require_scan_arg,
            spawn_x_arg,
            spawn_y_arg,
            spawn_z_arg,
            gazebo,
            state_publisher,
            command_guard,
            spawn,
        ]
    )
