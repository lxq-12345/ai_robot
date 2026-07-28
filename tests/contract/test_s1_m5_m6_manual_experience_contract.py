from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONSOLE = (
    PROJECT_ROOT
    / "src"
    / "ai_robot_sim"
    / "ai_robot_sim"
    / "manual_m5_m6_experience.py"
)
STARTER = PROJECT_ROOT / "scripts" / "start_m5_m6_manual_experience.sh"
SCENARIO = (
    PROJECT_ROOT
    / "tests"
    / "scenario"
    / "S1-M5-M6人工体验验收.md"
)


def test_manual_console_uses_actions_and_guarded_observation_only():
    source = CONSOLE.read_text(encoding="utf-8")

    assert '"/navigate_to_pose"' in source
    assert '"/execute_capability_task"' in source
    assert '"/safety_stop"' in source
    assert '"/cmd_vel"' in source
    assert 'create_publisher(Twist, "/cmd_vel"' not in source
    assert 'create_publisher(Twist, "/cmd_vel_raw"' not in source


def test_manual_console_covers_m5_m6_human_scenarios():
    source = CONSOLE.read_text(encoding="utf-8")

    assert "cancel_goal_async" in source
    assert "replayed" in source
    assert "SAFETY_TRIGGERED" in source
    assert "minimum_scan_range" in source
    assert "image_width" in source
    assert "input(" in source


def test_manual_starter_and_acceptance_checklist_are_present():
    starter = STARTER.read_text(encoding="utf-8")
    scenario = SCENARIO.read_text(encoding="utf-8")

    assert "m6_bringup.launch.py gui:=true" in starter
    assert "manual_m5_m6_experience --scenario all" in starter
    assert "Gazebo" in scenario
    assert "全部项目均为`PASS`" in scenario
