from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SIM_LAUNCH = PACKAGE_ROOT / "launch" / "sim_bringup.launch.py"
MANUAL_DEMO = PACKAGE_ROOT / "ai_robot_sim" / "manual_motion_demo.py"


def test_sim_bringup_exposes_gui_launch_argument():
    launch_source = SIM_LAUNCH.read_text(encoding="utf-8")

    assert 'DeclareLaunchArgument(\n        "gui"' in launch_source
    assert 'default_value="false"' in launch_source
    assert '"gui": gui' in launch_source


def test_manual_motion_demo_uses_raw_command_topic_only():
    demo_source = MANUAL_DEMO.read_text(encoding="utf-8")

    assert 'create_publisher(Twist, "/cmd_vel_raw", 10)' in demo_source
    assert '"/cmd_vel"' not in demo_source
