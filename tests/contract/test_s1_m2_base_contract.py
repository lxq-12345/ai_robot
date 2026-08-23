import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
XACRO_FILE = PROJECT_ROOT / "src" / "ai_robot_description" / "urdf" / "ai_robot.urdf.xacro"
SIM_CONFIG = PROJECT_ROOT / "config" / "sim_base.yaml"


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


def test_robot_model_defines_required_base_and_sensor_frames():
    robot = expanded_robot_description()
    links = {link.attrib["name"] for link in robot.findall("link")}
    joints = {joint.attrib["name"]: joint for joint in robot.findall("joint")}

    assert {
        "base_footprint",
        "base_link",
        "left_wheel",
        "right_wheel",
        "laser_link",
        "camera_link",
        "imu_link",
    } <= links
    assert {"left_wheel_joint", "right_wheel_joint", "laser_joint", "camera_joint", "imu_joint"} <= joints.keys()
    assert joints["base_footprint_joint"].attrib["type"] == "fixed"

    assert joints["left_wheel_joint"].attrib["type"] == "continuous"
    assert joints["right_wheel_joint"].attrib["type"] == "continuous"
    assert joints["laser_joint"].attrib["type"] == "fixed"
    assert joints["camera_joint"].attrib["type"] == "fixed"
    assert joints["imu_joint"].attrib["type"] == "fixed"
    assert joints["left_wheel_joint"].find("axis").attrib["xyz"] == "0 1 0"
    assert joints["right_wheel_joint"].find("axis").attrib["xyz"] == "0 1 0"


def test_gazebo_diff_drive_plugin_matches_public_base_interface():
    robot = expanded_robot_description()
    plugins = robot.findall("gazebo/plugin")
    diff_drive = next(
        plugin for plugin in plugins if plugin.attrib.get("filename") == "libgazebo_ros_diff_drive.so"
    )

    assert child_text(diff_drive, "left_joint") == "left_wheel_joint"
    assert child_text(diff_drive, "right_joint") == "right_wheel_joint"
    assert child_text(diff_drive, "odometry_topic") == "odom"
    assert child_text(diff_drive, "odometry_frame") == "odom"
    assert child_text(diff_drive, "robot_base_frame") == "base_footprint"
    assert child_text(diff_drive, "publish_odom") == "true"
    assert child_text(diff_drive, "publish_odom_tf") == "true"


def test_gazebo_joint_state_plugin_publishes_wheel_states():
    robot = expanded_robot_description()
    plugins = robot.findall("gazebo/plugin")
    joint_states = next(
        plugin
        for plugin in plugins
        if plugin.attrib.get("filename") == "libgazebo_ros_joint_state_publisher.so"
    )

    assert child_text(joint_states, "update_rate") == "50"
    assert [joint.text for joint in joint_states.findall("joint_name")] == [
        "left_wheel_joint",
        "right_wheel_joint",
    ]


def test_sim_base_limits_are_positive_and_match_m2_safety_bounds():
    with SIM_CONFIG.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    params = config["cmd_vel_guard"]["ros__parameters"]
    assert 0.0 < params["max_linear_speed"] <= 0.35
    assert 0.0 < params["max_angular_speed"] <= 1.20
    assert 0.0 < params["command_timeout"] <= 0.50
