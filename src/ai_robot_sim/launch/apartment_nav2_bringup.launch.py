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
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    gui = LaunchConfiguration("gui")
    rviz = LaunchConfiguration("rviz")
    gui_arg = DeclareLaunchArgument("gui", default_value="false")
    rviz_arg = DeclareLaunchArgument("rviz", default_value="false")
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{sim_share}/launch/apartment_house_bringup.launch.py"
        ),
        launch_arguments={
            "gui": gui,
            "require_scan": "true",
            # Nav2's velocity smoother owns /cmd_vel.  The guard is the only
            # publisher allowed to command the Gazebo base on /cmd_vel_safe.
            "command_input_topic": "/cmd_vel",
        }.items(),
    )
    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        parameters=[
            {
                "use_sim_time": True,
                "yaml_filename": f"{sim_share}/maps/apartment_v1.3_nav.yaml",
            }
        ],
        output="screen",
    )
    amcl = Node(
        package="nav2_amcl",
        executable="amcl",
        parameters=[
            f"{sim_share}/config/amcl_sim.yaml",
            {"initial_pose.x": 1.80, "initial_pose.y": 4.00},
        ],
        output="screen",
    )
    localization_lifecycle = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_localization",
        parameters=[
            {
                "use_sim_time": True,
                "autostart": True,
                "node_names": ["map_server", "amcl"],
            }
        ],
        output="screen",
    )
    nav2_params = RewrittenYaml(
        source_file=f"{sim_share}/config/nav2_sim.yaml",
        root_key="",
        param_rewrites={
            "default_nav_to_pose_bt_xml": (
                f"{sim_share}/behavior_trees/"
                "navigate_to_pose_back_up_recovery.xml"
            ),
            "default_nav_through_poses_bt_xml": (
                f"{sim_share}/behavior_trees/"
                "navigate_through_poses_back_up_recovery.xml"
            ),
        },
        convert_types=True,
    )
    navigation = GroupAction(
        [
            SetRemap(src="/cmd_vel", dst="/cmd_vel_raw"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    f"{get_package_share_directory('nav2_bringup')}/launch/navigation_launch.py"
                ),
                launch_arguments={
                    "use_sim_time": "true",
                    "use_composition": "False",
                    "params_file": nav2_params,
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
            f"{sim_share}/config/au9_nav2.rviz",
        ],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(rviz),
        output="screen",
    )
    return LaunchDescription(
        [
            gui_arg,
            rviz_arg,
            simulation,
            map_server,
            amcl,
            localization_lifecycle,
            TimerAction(period=10.0, actions=[navigation]),
            TimerAction(period=12.0, actions=[rviz_node]),
        ]
    )
