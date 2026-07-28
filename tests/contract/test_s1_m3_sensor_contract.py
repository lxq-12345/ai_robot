import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
XACRO_FILE = PROJECT_ROOT / "src" / "ai_robot_description" / "urdf" / "ai_robot.urdf.xacro"
SENSOR_CONFIG = PROJECT_ROOT / "config" / "sim_sensors.yaml"
DIAGNOSTICS_CONFIG = PROJECT_ROOT / "config" / "sim_sensor_diagnostics.yaml"


def expanded_robot_description():
    result = subprocess.run(
        ["xacro", str(XACRO_FILE)],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def child_text(element, tag):
    child = element.find(tag)
    assert child is not None, f"missing <{tag}> in {element.tag}"
    assert child.text is not None, f"missing text for <{tag}> in {element.tag}"
    return child.text


def gazebo_reference(robot, link_name):
    return next(gazebo for gazebo in robot.findall("gazebo") if gazebo.attrib.get("reference") == link_name)


def test_laser_sensor_contract_matches_baseline():
    robot = expanded_robot_description()
    sensor = gazebo_reference(robot, "laser_link").find("sensor")
    plugin = sensor.find("plugin")

    assert sensor.attrib["type"] == "ray"
    assert child_text(sensor, "update_rate") == "10"
    assert plugin.attrib["filename"] == "libgazebo_ros_ray_sensor.so"
    assert child_text(plugin, "output_type") == "sensor_msgs/LaserScan"
    assert child_text(plugin, "frame_name") == "laser_link"
    assert plugin.find("ros/remapping").text == "~/out:=/scan"
    assert child_text(sensor.find("ray/scan/horizontal"), "samples") == "360"
    assert child_text(sensor.find("ray/range"), "min") == "0.12"
    assert child_text(sensor.find("ray/range"), "max") == "8.0"


def test_camera_sensor_contract_matches_baseline():
    robot = expanded_robot_description()
    sensor = gazebo_reference(robot, "camera_link").find("sensor")
    plugin = sensor.find("plugin")

    assert sensor.attrib["type"] == "camera"
    assert child_text(sensor, "update_rate") == "10"
    assert plugin.attrib["filename"] == "libgazebo_ros_camera.so"
    assert child_text(plugin, "camera_name") == "camera"
    assert child_text(plugin, "frame_name") == "camera_link"
    remaps = [remap.text for remap in plugin.findall("ros/remapping")]
    assert "image_raw:=/camera/image_raw" in remaps
    assert "camera_info:=/camera/camera_info" in remaps
    assert child_text(sensor.find("camera/image"), "width") == "640"
    assert child_text(sensor.find("camera/image"), "height") == "480"
    assert child_text(sensor.find("camera/image"), "format") == "R8G8B8"


def test_imu_sensor_contract_matches_baseline():
    robot = expanded_robot_description()
    sensor = gazebo_reference(robot, "imu_link").find("sensor")
    plugin = sensor.find("plugin")

    assert sensor.attrib["type"] == "imu"
    assert child_text(sensor, "update_rate") == "50"
    assert plugin.attrib["filename"] == "libgazebo_ros_imu_sensor.so"
    assert plugin.find("ros/remapping").text == "~/out:=/imu/data"
    assert child_text(plugin, "frame_name") == "imu_link"
    assert child_text(plugin, "initial_orientation_as_reference") == "false"


def test_sim_sensor_parameter_file_tracks_required_topics_and_frames():
    with SENSOR_CONFIG.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)["sim_sensors"]

    assert config["laser"]["topic"] == "/scan"
    assert config["laser"]["frame_id"] == "laser_link"
    assert config["camera"]["image_topic"] == "/camera/image_raw"
    assert config["camera"]["info_topic"] == "/camera/camera_info"
    assert config["camera"]["frame_id"] == "camera_link"
    assert config["imu"]["topic"] == "/imu/data"
    assert config["imu"]["frame_id"] == "imu_link"
    assert config["encoder"]["topic"] == "/joint_states"
    assert config["encoder"]["left_joint"] == "left_wheel_joint"
    assert config["encoder"]["right_joint"] == "right_wheel_joint"


def test_sensor_diagnostics_config_tracks_frequency_and_stale_message_rules():
    with DIAGNOSTICS_CONFIG.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)["diagnostics"]

    sensors = config["sensors"]
    assert sensors["laser"]["topic"] == "/scan"
    assert sensors["laser"]["min_frequency_hz"] >= 5.0
    assert sensors["camera_image"]["topic"] == "/camera/image_raw"
    assert sensors["camera_info"]["topic"] == "/camera/camera_info"
    assert sensors["imu"]["topic"] == "/imu/data"
    assert sensors["imu"]["min_frequency_hz"] >= 25.0
    assert sensors["encoder"]["topic"] == "/joint_states"
    assert sensors["encoder"]["joints"] == ["left_wheel_joint", "right_wheel_joint"]
    assert any("Missing topic" in rule for rule in config["rules"])
