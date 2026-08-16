import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


XACRO_FILE = Path(__file__).resolve().parents[1] / "urdf" / "ai_robot.urdf.xacro"


def expand_xacro():
    return subprocess.run(
        ["xacro", str(XACRO_FILE)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_xacro_expands_to_parseable_urdf():
    urdf = expand_xacro()
    robot = ET.fromstring(urdf)

    assert robot.tag == "robot"
    assert robot.attrib["name"] == "ai_robot"


def test_expanded_urdf_contains_no_xacro_elements():
    robot = ET.fromstring(expand_xacro())

    assert not any("xacro" in element.tag for element in robot.iter())
