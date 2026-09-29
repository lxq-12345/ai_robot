import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SIM_LAUNCH = PACKAGE_ROOT / "launch" / "sim_bringup.launch.py"
NAV2_LAUNCH = PACKAGE_ROOT / "launch" / "nav2_bringup.launch.py"
APARTMENT_LAUNCH = PACKAGE_ROOT / "launch" / "apartment_house_bringup.launch.py"
APARTMENT_NAV2_LAUNCH = PACKAGE_ROOT / "launch" / "apartment_nav2_bringup.launch.py"
APARTMENT_WORLD = PACKAGE_ROOT / "worlds" / "apartment_v1.3.world"
APARTMENT_MAP_YAML = PACKAGE_ROOT / "maps" / "apartment_v1.3_nav.yaml"
APARTMENT_MAP_PGM = PACKAGE_ROOT / "maps" / "apartment_v1.3_nav.pgm"
AU9_RVIZ_CONFIG = (
    PACKAGE_ROOT.parents[1] / "config" / "rviz2" / "au9_nav2.rviz"
)
AMCL_CONFIG = PACKAGE_ROOT.parents[1] / "config" / "amcl_sim.yaml"
APARTMENT_ROBOT_SDF = (
    Path(__file__).resolve().parents[2]
    / "ai_robot_description"
    / "models"
    / "small_yellow_car_v1.2.sdf"
)
MANUAL_DEMO = PACKAGE_ROOT / "ai_robot_sim" / "manual_motion_demo.py"
AU8_GAZEBO_SCRIPT = PACKAGE_ROOT.parents[1] / "scripts" / "start_au8_gazebo.sh"
AU8_RVIZ_SCRIPT = PACKAGE_ROOT.parents[1] / "scripts" / "start_au8_rviz2.sh"
AU8_SYNC_CHECK = (
    PACKAGE_ROOT.parents[1] / "scripts" / "check_au8_gazebo_rviz2_sync.sh"
)
AU8_RVIZ_CONFIG = (
    PACKAGE_ROOT.parents[1] / "config" / "rviz2" / "small_yellow_car.rviz"
)


def test_sim_bringup_exposes_gui_launch_argument():
    launch_source = SIM_LAUNCH.read_text(encoding="utf-8")

    assert 'DeclareLaunchArgument(\n        "gui"' in launch_source
    assert 'default_value="false"' in launch_source
    assert '"gui": gui' in launch_source


def test_nav2_bringup_starts_rviz_with_sim_time_after_localization():
    launch_source = NAV2_LAUNCH.read_text(encoding="utf-8")

    assert 'DeclareLaunchArgument(\n        "rviz"' in launch_source
    assert 'package="rviz2"' in launch_source
    assert 'parameters=[{"use_sim_time": True}]' in launch_source
    assert "condition=IfCondition(rviz)" in launch_source
    assert "TimerAction(period=10.0, actions=[rviz_node])" in launch_source


def test_amcl_uses_known_sim_spawn_as_initial_pose():
    config_source = AMCL_CONFIG.read_text(encoding="utf-8")

    assert "set_initial_pose: true" in config_source
    assert "initial_pose:" in config_source
    assert "x: 0.0" in config_source
    assert "y: 0.0" in config_source
    assert "yaw: 0.0" in config_source


def test_sim_bringup_exposes_robot_spawn_position_arguments():
    launch_source = SIM_LAUNCH.read_text(encoding="utf-8")

    for argument in ("spawn_x", "spawn_y", "spawn_z"):
        assert f'DeclareLaunchArgument(\n        "{argument}"' in launch_source
        assert f'LaunchConfiguration("{argument}")' in launch_source


def test_sim_bringup_exposes_robot_model_argument():
    launch_source = SIM_LAUNCH.read_text(encoding="utf-8")

    assert 'DeclareLaunchArgument(\n        "robot_model"' in launch_source
    assert 'LaunchConfiguration("robot_model")' in launch_source


def test_apartment_world_is_valid_self_contained_sdf():
    root = ET.parse(APARTMENT_WORLD).getroot()
    world = root.find("world")

    assert root.tag == "sdf"
    assert root.attrib["version"] == "1.6"
    assert world is not None
    assert world.attrib["name"] == "apartment_house_merged_v1_3"
    assert world.find("model[@name='apartment_house']") is not None
    assert world.findall(".//include") == []
    assert world.findtext("gui/camera/view_controller") == "orbit"
    assert world.findtext("gui/camera/projection_type") == "perspective"


def test_apartment_bringup_uses_project_world_and_safe_spawn_point():
    launch_source = APARTMENT_LAUNCH.read_text(encoding="utf-8")

    assert '"world": f"{sim_share}/worlds/apartment_v1.3.world"' in launch_source
    assert '"spawn_x": "1.80"' in launch_source
    assert '"spawn_y": "4.00"' in launch_source
    assert '"spawn_z": "0.10"' in launch_source
    assert '"robot_model": f"{description_share}/urdf/small_yellow_car_v1.2.urdf.xacro"' in launch_source
    assert '"robot_sdf": f"{description_share}/models/small_yellow_car_v1.2.sdf"' in launch_source
    assert '"spawn_from_sdf": "true"' in launch_source
    assert '"require_scan": require_scan' in launch_source


def test_apartment_nav2_bringup_reuses_au8_world_robot_and_map():
    launch_source = APARTMENT_NAV2_LAUNCH.read_text(encoding="utf-8")
    rviz_source = AU9_RVIZ_CONFIG.read_text(encoding="utf-8")

    assert "apartment_house_bringup.launch.py" in launch_source
    assert '"require_scan": "true"' in launch_source
    assert "apartment_v1.3_nav.yaml" in launch_source
    assert '"initial_pose.x": 1.80' in launch_source
    assert '"initial_pose.y": 4.00' in launch_source
    assert 'SetRemap(src="/cmd_vel", dst="/cmd_vel_raw")' in launch_source
    assert 'f"{sim_share}/config/au9_nav2.rviz"' in launch_source
    assert "Fixed Frame: map" in rviz_source
    assert "Reference Frame: map" in rviz_source
    assert "Plane Cell Count: 20" in rviz_source
    assert "Offset:\n        X: 0\n        Y: 0\n        Z: -0.01" in rviz_source
    assert "X: 3.1" in rviz_source
    assert "Y: 3.75" in rviz_source
    assert "Class: nav2_rviz_plugins/GoalTool" in rviz_source
    assert "Class: nav2_rviz_plugins/Navigation 2" in rviz_source
    assert APARTMENT_MAP_YAML.is_file()
    assert APARTMENT_MAP_PGM.is_file()


def test_apartment_navigation_map_has_expected_frame_and_free_test_points():
    yaml_source = APARTMENT_MAP_YAML.read_text(encoding="utf-8")
    assert "image: apartment_v1.3_nav.pgm" in yaml_source
    assert "resolution: 0.05" in yaml_source
    assert "origin: [-0.50, -0.50, 0.0]" in yaml_source

    with APARTMENT_MAP_PGM.open("rb") as stream:
        assert stream.readline().strip() == b"P5"
        width, height = [int(value) for value in stream.readline().split()]
        assert stream.readline().strip() == b"255"
        pixels = stream.read()
    assert (width, height) == (144, 170)
    assert len(pixels) == width * height

    def occupancy_at(x, y):
        column = int((x + 0.50) / 0.05)
        map_row = int((y + 0.50) / 0.05)
        image_row = height - 1 - map_row
        return pixels[image_row * width + column]

    for point in ((1.80, 4.00), (1.50, 4.00), (1.20, 4.00), (1.80, 5.80)):
        assert occupancy_at(*point) == 254
    assert occupancy_at(0.10, 4.00) == 0
    assert occupancy_at(3.08, 5.80) == 0


def test_apartment_ground_visual_matches_navigation_map_extent():
    root = ET.parse(APARTMENT_WORLD).getroot()
    ground = root.find("world/model[@name='ground']")
    visual = ground.find("./link/visual[@name='floor_visual']")
    collision = ground.find("./link/collision[@name='floor_collision']")

    model_pose = [float(value) for value in ground.findtext("pose").split()]
    visual_pose = [float(value) for value in visual.findtext("pose").split()]
    visual_size = [
        float(value) for value in visual.findtext("geometry/box/size").split()
    ]
    collision_size = [
        float(value) for value in collision.findtext("geometry/box/size").split()
    ]

    assert abs(model_pose[0] + visual_pose[0] - 3.10) < 1e-9
    assert abs(model_pose[1] + visual_pose[1] - 3.75) < 1e-9
    assert visual_size[:2] == [7.20, 8.50]
    assert visual_pose[2] < 0.0
    assert collision_size[:2] == [12.19, 13.48]


def test_apartment_robot_sdf_has_explicit_yellow_body_material():
    root = ET.parse(APARTMENT_ROBOT_SDF).getroot()
    body_visual = next(
        visual
        for visual in root.findall(".//visual")
        if "body_visual" in visual.attrib.get("name", "")
    )
    material = body_visual.find("material")

    assert material is not None
    assert material.findtext("ambient") == "0.95 0.65 0.05 1"
    assert material.findtext("diffuse") == "0.95 0.65 0.05 1"


def test_au8_separate_entries_use_yellow_car_cameras_and_project_rviz():
    gazebo_source = AU8_GAZEBO_SCRIPT.read_text(encoding="utf-8")
    rviz_entry_source = AU8_RVIZ_SCRIPT.read_text(encoding="utf-8")
    check_source = AU8_SYNC_CHECK.read_text(encoding="utf-8")
    rviz_source = AU8_RVIZ_CONFIG.read_text(encoding="utf-8")

    assert "apartment_house_bringup.launch.py gui:=true" in gazebo_source
    assert "rviz2" not in gazebo_source
    assert 'rviz_config="${workspace_dir}/config/rviz2/small_yellow_car.rviz"' in rviz_entry_source
    assert "apartment_house_bringup" not in rviz_entry_source
    assert "use_sim_time:=true" in rviz_entry_source
    for topic in (
        "/camera/image_raw",
        "/camera/camera_info",
        "/camera/right/image_raw",
        "/camera/right/camera_info",
    ):
        assert topic in check_source
    assert "camera_left_optical_frame" in check_source
    assert "camera_right_optical_frame" in check_source
    assert "Class: rviz_default_plugins/Camera" in rviz_source
    assert "Name: Camera Left" in rviz_source
    assert "Class: rviz_default_plugins/Image" in rviz_source
    assert "Name: Image Right" in rviz_source
    assert rviz_source.count("Topic: /camera/image_raw") == 1
    assert rviz_source.count("Topic: /camera/right/image_raw") == 1


def test_manual_motion_demo_uses_raw_command_topic_only():
    demo_source = MANUAL_DEMO.read_text(encoding="utf-8")

    assert 'create_publisher(Twist, "/cmd_vel_raw", 10)' in demo_source
    assert '"/cmd_vel"' not in demo_source
