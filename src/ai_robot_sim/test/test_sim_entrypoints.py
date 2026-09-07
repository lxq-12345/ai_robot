import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SIM_LAUNCH = PACKAGE_ROOT / "launch" / "sim_bringup.launch.py"
APARTMENT_LAUNCH = PACKAGE_ROOT / "launch" / "apartment_house_bringup.launch.py"
APARTMENT_WORLD = PACKAGE_ROOT / "worlds" / "apartment_house_merged_v1.3.world"
MANUAL_DEMO = PACKAGE_ROOT / "ai_robot_sim" / "manual_motion_demo.py"


def test_sim_bringup_exposes_gui_launch_argument():
    launch_source = SIM_LAUNCH.read_text(encoding="utf-8")

    assert 'DeclareLaunchArgument(\n        "gui"' in launch_source
    assert 'default_value="false"' in launch_source
    assert '"gui": gui' in launch_source


def test_sim_bringup_exposes_robot_spawn_position_arguments():
    launch_source = SIM_LAUNCH.read_text(encoding="utf-8")

    for argument in ("spawn_x", "spawn_y", "spawn_z"):
        assert f'DeclareLaunchArgument(\n        "{argument}"' in launch_source
        assert f'LaunchConfiguration("{argument}")' in launch_source


def test_apartment_world_is_valid_self_contained_sdf():
    root = ET.parse(APARTMENT_WORLD).getroot()
    world = root.find("world")

    assert root.tag == "sdf"
    assert root.attrib["version"] == "1.6"
    assert world is not None
    assert world.attrib["name"] == "apartment_house_merged_v1_3"
    assert world.find("model[@name='apartment_house']") is not None
    assert world.findall(".//include") == []


def test_apartment_bringup_uses_project_world_and_safe_spawn_point():
    launch_source = APARTMENT_LAUNCH.read_text(encoding="utf-8")

    assert '"world": f"{sim_share}/worlds/apartment_house_merged_v1.3.world"' in launch_source
    assert '"spawn_x": "1.80"' in launch_source
    assert '"spawn_y": "4.00"' in launch_source
    assert '"spawn_z": "0.10"' in launch_source


def test_manual_motion_demo_uses_raw_command_topic_only():
    demo_source = MANUAL_DEMO.read_text(encoding="utf-8")

    assert 'create_publisher(Twist, "/cmd_vel_raw", 10)' in demo_source
    assert '"/cmd_vel"' not in demo_source
