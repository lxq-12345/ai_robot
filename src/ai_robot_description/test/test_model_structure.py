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


def joint_definition(joint):
    return (
        joint.attrib["type"],
        joint.find("parent").attrib["link"],
        joint.find("child").attrib["link"],
    )


def test_required_links_are_present():
    links = {link.attrib["name"] for link in expanded_robot().findall("link")}

    assert links == {
        "base_footprint",
        "base_link",
        "left_wheel",
        "right_wheel",
        "laser_link",
        "camera_link",
        "imu_link",
    }


def test_joint_types_and_parent_child_relationships_match_baseline():
    joints = {
        joint.attrib["name"]: joint_definition(joint)
        for joint in expanded_robot().findall("joint")
    }

    assert joints == {
        "base_footprint_joint": ("fixed", "base_footprint", "base_link"),
        "left_wheel_joint": ("continuous", "base_link", "left_wheel"),
        "right_wheel_joint": ("continuous", "base_link", "right_wheel"),
        "laser_joint": ("fixed", "base_link", "laser_link"),
        "camera_joint": ("fixed", "base_link", "camera_link"),
        "imu_joint": ("fixed", "base_link", "imu_link"),
    }


def test_wheel_axes_and_mounting_positions_match_baseline():
    joints = {
        joint.attrib["name"]: joint for joint in expanded_robot().findall("joint")
    }

    assert joints["left_wheel_joint"].find("axis").attrib["xyz"] == "0 1 0"
    assert joints["right_wheel_joint"].find("axis").attrib["xyz"] == "0 1 0"
    assert joints["left_wheel_joint"].find("origin").attrib["xyz"] == "0 0.18 0.075"
    assert joints["right_wheel_joint"].find("origin").attrib["xyz"] == "0 -0.18 0.075"


def test_every_non_root_link_has_exactly_one_parent_joint():
    robot = expanded_robot()
    links = {link.attrib["name"] for link in robot.findall("link")}
    children = [joint.find("child").attrib["link"] for joint in robot.findall("joint")]

    assert set(children) == links - {"base_footprint"}
    assert len(children) == len(set(children))
