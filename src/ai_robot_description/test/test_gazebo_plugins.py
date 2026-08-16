import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


XACRO_FILE = Path(__file__).resolve().parents[1] / "urdf" / "ai_robot.urdf.xacro"


def expanded_robot():
    result = subprocess.run(
        ["xacro", str(XACRO_FILE)],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def child_text(element, tag):
    child = element.find(tag)
    assert child is not None, f"missing <{tag}>"
    assert child.text is not None, f"missing value for <{tag}>"
    return child.text


def plugin_by_filename(robot, filename):
    return next(
        plugin
        for plugin in robot.findall(".//plugin")
        if plugin.attrib.get("filename") == filename
    )


def sensor_for_link(robot, link_name):
    gazebo = next(
        element
        for element in robot.findall("gazebo")
        if element.attrib.get("reference") == link_name
    )
    return gazebo.find("sensor")


def test_diff_drive_plugin_matches_base_interface():
    plugin = plugin_by_filename(expanded_robot(), "libgazebo_ros_diff_drive.so")

    assert child_text(plugin, "left_joint") == "left_wheel_joint"
    assert child_text(plugin, "right_joint") == "right_wheel_joint"
    assert child_text(plugin, "wheel_separation") == "0.36"
    assert child_text(plugin, "wheel_diameter") == "0.15"
    assert child_text(plugin, "odometry_topic") == "odom"
    assert child_text(plugin, "odometry_frame") == "odom"
    assert child_text(plugin, "robot_base_frame") == "base_link"
    assert child_text(plugin, "publish_odom") == "true"
    assert child_text(plugin, "publish_odom_tf") == "true"


def test_joint_state_plugin_tracks_both_wheels():
    plugin = plugin_by_filename(
        expanded_robot(), "libgazebo_ros_joint_state_publisher.so"
    )

    assert child_text(plugin, "update_rate") == "50"
    assert [joint.text for joint in plugin.findall("joint_name")] == [
        "left_wheel_joint",
        "right_wheel_joint",
    ]


def test_laser_description_matches_interface_baseline():
    sensor = sensor_for_link(expanded_robot(), "laser_link")
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


def test_camera_description_matches_interface_baseline():
    sensor = sensor_for_link(expanded_robot(), "camera_link")
    plugin = sensor.find("plugin")

    assert sensor.attrib["type"] == "camera"
    assert child_text(sensor, "update_rate") == "10"
    assert plugin.attrib["filename"] == "libgazebo_ros_camera.so"
    assert child_text(plugin, "frame_name") == "camera_link"
    assert {remap.text for remap in plugin.findall("ros/remapping")} == {
        "image_raw:=/camera/image_raw",
        "camera_info:=/camera/camera_info",
    }
    assert child_text(sensor.find("camera/image"), "width") == "640"
    assert child_text(sensor.find("camera/image"), "height") == "480"


def test_imu_description_matches_interface_baseline():
    sensor = sensor_for_link(expanded_robot(), "imu_link")
    plugin = sensor.find("plugin")

    assert sensor.attrib["type"] == "imu"
    assert child_text(sensor, "update_rate") == "50"
    assert plugin.attrib["filename"] == "libgazebo_ros_imu_sensor.so"
    assert plugin.find("ros/remapping").text == "~/out:=/imu/data"
    assert child_text(plugin, "frame_name") == "imu_link"
    assert child_text(plugin, "initial_orientation_as_reference") == "false"
