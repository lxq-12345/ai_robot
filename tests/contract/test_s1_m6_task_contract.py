from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_capability_task_action_is_structured_and_stable():
    action = (
        ROOT
        / "src"
        / "ai_robot_interfaces"
        / "action"
        / "ExecuteCapabilityTask.action"
    ).read_text()
    assert "string task_id" in action
    assert "geometry_msgs/PoseStamped target_pose" in action
    assert "uint8 outcome" in action
    assert "bool replayed" in action
    assert "uint8 SAFETY_TRIGGERED=7" in action


def test_task_manager_uses_nav2_and_safety_guarded_interface():
    manager = (
        ROOT
        / "src"
        / "ai_robot_sim"
        / "ai_robot_sim"
        / "capability_task_manager.py"
    ).read_text()
    nav_launch = (
        ROOT
        / "src"
        / "ai_robot_sim"
        / "launch"
        / "nav2_bringup.launch.py"
    ).read_text()
    assert '"/navigate_to_pose"' in manager
    assert '"/safety_stop"' in manager
    assert 'SetRemap(src="/cmd_vel", dst="/cmd_vel_raw")' in nav_launch
    assert '"/cmd_vel"' not in manager


def test_m6_launch_does_not_start_ai_components():
    launch_file = (
        ROOT
        / "src"
        / "ai_robot_sim"
        / "launch"
        / "m6_bringup.launch.py"
    ).read_text()
    assert "capability_task_manager" in launch_file
    assert "nav2_bringup.launch.py" in launch_file
    assert "openai" not in launch_file.lower()
    assert "agent" not in launch_file.lower()
