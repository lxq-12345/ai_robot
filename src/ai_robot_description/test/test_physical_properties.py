import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


XACRO_FILE = Path(__file__).resolve().parents[1] / "urdf" / "ai_robot.urdf.xacro"


def expanded_robot():
    result = subprocess.run(
        ["xacro", str(XACRO_FILE)],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def dynamic_links():
    return {
        link.attrib["name"]: link
        for link in expanded_robot().findall("link")
        if link.attrib["name"]
        in {
            "base_link",
            "left_front_wheel",
            "left_rear_wheel",
            "right_front_wheel",
            "right_rear_wheel",
        }
    }


def geometry_signature(geometry):
    shape = next(iter(geometry))
    return shape.tag, shape.attrib


@pytest.mark.parametrize(
    "link_name",
    [
        "base_link",
        "left_front_wheel",
        "left_rear_wheel",
        "right_front_wheel",
        "right_rear_wheel",
    ],
)
def test_dynamic_links_have_positive_mass_and_inertia(link_name):
    inertial = dynamic_links()[link_name].find("inertial")
    mass = float(inertial.find("mass").attrib["value"])
    inertia = inertial.find("inertia").attrib
    diagonal = [float(inertia[key]) for key in ("ixx", "iyy", "izz")]

    assert mass > 0.0
    assert all(value > 0.0 for value in diagonal)
    assert diagonal[0] + diagonal[1] >= diagonal[2]
    assert diagonal[0] + diagonal[2] >= diagonal[1]
    assert diagonal[1] + diagonal[2] >= diagonal[0]


@pytest.mark.parametrize(
    "link_name",
    [
        "base_link",
        "left_front_wheel",
        "left_rear_wheel",
        "right_front_wheel",
        "right_rear_wheel",
    ],
)
def test_dynamic_links_have_matching_visual_and_collision_geometry(link_name):
    link = dynamic_links()[link_name]
    visual_geometry = geometry_signature(link.find("visual/geometry"))
    collision_geometry = geometry_signature(link.find("collision/geometry"))

    assert visual_geometry == collision_geometry


def test_base_and_wheel_dimensions_match_baseline():
    links = dynamic_links()
    base_size = links["base_link"].find("visual/geometry/box").attrib["size"]
    wheel_geometry = {"radius": "0.075", "length": "0.035"}

    assert base_size == "0.52 0.36 0.16"
    assert links["left_front_wheel"].find("visual/geometry/cylinder").attrib == wheel_geometry
    assert links["left_rear_wheel"].find("visual/geometry/cylinder").attrib == wheel_geometry
    assert links["right_front_wheel"].find("visual/geometry/cylinder").attrib == wheel_geometry
    assert links["right_rear_wheel"].find("visual/geometry/cylinder").attrib == wheel_geometry
