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


@pytest.mark.parametrize('model_format', ['xacro', 'sdf'])
def test_yellow_car_drive_parameters_match_both_physical_wheel_pairs(model_format):
    package = XACRO_FILE.parents[1]
    if model_format == 'xacro':
        expanded = subprocess.run(
            ['xacro', str(package / 'urdf/small_yellow_car_v1.2.urdf.xacro')],
            check=True, capture_output=True, text=True,
        )
        robot = ET.fromstring(expanded.stdout)
    else:
        robot = ET.parse(package / 'models/small_yellow_car_v1.2.sdf').getroot().find('model')
    plugin = next(p for p in robot.findall('.//plugin')
                  if p.get('filename') == 'libgazebo_ros_diff_drive.so')
    pairs = int(plugin.findtext('num_wheel_pairs'))
    left = plugin.findall('left_joint')
    right = plugin.findall('right_joint')
    separations = plugin.findall('wheel_separation')
    diameters = plugin.findall('wheel_diameter')
    assert len(left) == len(right) == len(separations) == len(diameters) == pairs
    for i in range(pairs):
        joints = [robot.find(f"joint[@name='{side[i].text}']") for side in (left, right)]
        if model_format == 'xacro':
            poses = [list(map(float, j.find('origin').get('xyz').split())) for j in joints]
            child = joints[0].find('child').get('link')
            radius = float(robot.find(f"link[@name='{child}']/collision/geometry/cylinder").get('radius'))
        else:
            poses = [list(map(float, j.findtext('pose').split()[:3])) for j in joints]
            child = joints[0].findtext('child')
            radius = float(robot.findtext(f"link[@name='{child}']/collision/geometry/cylinder/radius"))
        assert float(separations[i].text) == pytest.approx(abs(poses[0][1]-poses[1][1]))
        assert float(diameters[i].text) == pytest.approx(2*radius)
