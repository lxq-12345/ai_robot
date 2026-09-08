from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    description_share = get_package_share_directory("ai_robot_description")
    sim_share = get_package_share_directory("ai_robot_sim")
    gui = LaunchConfiguration("gui")
    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="true",
        description="Start Gazebo Classic with the apartment graphical view.",
    )
    bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(f"{sim_share}/launch/sim_bringup.launch.py"),
        launch_arguments={
            "gui": gui,
            "world": f"{sim_share}/worlds/apartment_house_merged_v1.3.world",
            "spawn_x": "1.80",
            "spawn_y": "4.00",
            "spawn_z": "0.10",
            "robot_model": f"{description_share}/urdf/small_yellow_car_v1.2.urdf.xacro",
        }.items(),
    )
    return LaunchDescription([gui_arg, bringup])
