import os
import tempfile
import unittest

import launch
import launch.actions
import launch.events
import launch_testing
import pytest
from launch_ros.actions import Node


ros_log_dir = tempfile.mkdtemp(prefix="ai_robot_py_example_ros_log_")
os.environ.setdefault("ROS_LOG_DIR", ros_log_dir)


@pytest.mark.launch_test
def generate_test_description():
    baseline_node = Node(
        package="ai_robot_py_example",
        executable="baseline_node",
        output="screen",
    )

    return (
        launch.LaunchDescription(
            [
                baseline_node,
                launch_testing.actions.ReadyToTest(),
                launch.actions.TimerAction(
                    period=3.0,
                    actions=[
                        launch.actions.EmitEvent(event=launch.events.Shutdown())
                    ],
                ),
            ]
        ),
        {"baseline_node": baseline_node},
    )


class TestBaselinePyNodeLaunch(unittest.TestCase):
    def test_process_reports_ready(self, proc_output, baseline_node):
        proc_output.assertWaitFor(
            "ai_robot_py_example:ready",
            process=baseline_node,
            timeout=10,
        )


@launch_testing.post_shutdown_test()
class TestBaselinePyNodeShutdown(unittest.TestCase):
    def test_baseline_node_exits_cleanly(self, proc_info, baseline_node):
        launch_testing.asserts.assertExitCodes(proc_info, process=baseline_node)
