from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE = PROJECT_ROOT / "config" / "ros_interface_baseline.yaml"


def test_required_topics_and_qos_profiles_exist():
    with BASELINE.open(encoding="utf-8") as stream:
        baseline = yaml.safe_load(stream)

    assert baseline["topics"]["command_velocity"]["name"] == "/cmd_vel"
    assert baseline["topics"]["odometry"]["name"] == "/odom"
    assert baseline["topics"]["laser_scan"]["name"] == "/scan"
    assert baseline["qos_profiles"]["sensor_data"]["reliability"] == "best_effort"
    assert baseline["qos_profiles"]["reliable_depth_10"]["reliability"] == "reliable"
