import unittest

import launch
import launch.actions
import launch.events
import launch_testing
import pytest
from launch_ros.actions import Node


@pytest.mark.launch_test
def generate_test_description():
    cpp_node = Node(
        package="ai_robot_cpp_example",
        executable="baseline_node",
        output="screen",
    )
    python_node = Node(
        package="ai_robot_py_example",
        executable="baseline_node",
        output="screen",
    )
    return (
        launch.LaunchDescription(
            [
                cpp_node,
                python_node,
                launch_testing.actions.ReadyToTest(),
                launch.actions.TimerAction(
                    period=10.0,
                    actions=[
                        launch.actions.EmitEvent(event=launch.events.Shutdown())
                    ],
                ),
            ]
        ),
        {"cpp_node": cpp_node, "python_node": python_node},
    )


class TestMinimalNodes(unittest.TestCase):
    def test_cpp_node_reports_ready(self, proc_output, cpp_node):
        proc_output.assertWaitFor(
            "ai_robot_cpp_example:ready", process=cpp_node, timeout=10
        )

    def test_python_node_reports_ready(self, proc_output, python_node):
        proc_output.assertWaitFor(
            "ai_robot_py_example:ready", process=python_node, timeout=10
        )


@launch_testing.post_shutdown_test()
class TestMinimalNodesShutdown(unittest.TestCase):
    def test_nodes_exit_cleanly(
        self, proc_info, cpp_node, python_node
    ):
        launch_testing.asserts.assertExitCodes(
            proc_info, process=cpp_node
        )
        launch_testing.asserts.assertExitCodes(
            proc_info, process=python_node
        )
