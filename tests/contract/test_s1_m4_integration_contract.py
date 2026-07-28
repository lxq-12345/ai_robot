from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EKF_CONFIG = PROJECT_ROOT / "config" / "ekf_sim.yaml"
DEPENDENCY_STATUS = PROJECT_ROOT / "config" / "s1_m4_dependency_status.yaml"


def test_robot_localization_ekf_config_tracks_odom_and_imu_inputs():
    with EKF_CONFIG.open(encoding="utf-8") as stream:
        params = yaml.safe_load(stream)["ekf_filter_node"]["ros__parameters"]

    assert params["frequency"] >= 30.0
    assert params["two_d_mode"] is True
    assert params["odom0"] == "/odom"
    assert params["imu0"] == "/imu/data"
    assert params["odom_frame"] == "odom"
    assert params["base_link_frame"] == "base_link"
    assert params["world_frame"] == "odom"


def test_missing_mature_dependencies_are_recorded_for_m4():
    with DEPENDENCY_STATUS.open(encoding="utf-8") as stream:
        deps = yaml.safe_load(stream)["s1_m4_dependencies"]

    assert deps["robot_localization"]["apt_package"] == "ros-humble-robot-localization"
    assert deps["robot_localization"]["status"] in ("available", "missing")
    assert deps["robot_localization"]["blocker"] == "sudo_password_required"
    assert deps["image_proc"]["apt_package"] == "ros-humble-image-proc"
    assert deps["image_proc"]["status"] in ("available", "missing")
    assert deps["cv_bridge"]["status"] == "available"
