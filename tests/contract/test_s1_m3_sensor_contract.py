from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SENSOR_CONFIG = PROJECT_ROOT / "config" / "sim_sensors.yaml"
DIAGNOSTICS_CONFIG = PROJECT_ROOT / "config" / "sim_sensor_diagnostics.yaml"


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
    assert config["encoder"]["left_joints"] == [
        "left_front_wheel_joint",
        "left_rear_wheel_joint",
    ]
    assert config["encoder"]["right_joints"] == [
        "right_front_wheel_joint",
        "right_rear_wheel_joint",
    ]


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
    assert sensors["encoder"]["joints"] == [
        "left_front_wheel_joint",
        "left_rear_wheel_joint",
        "right_front_wheel_joint",
        "right_rear_wheel_joint",
    ]
    assert any("Missing topic" in rule for rule in config["rules"])
