import time
import unittest

import launch
import launch.actions
import launch.events
import launch_testing
import pytest
import rclpy
from launch_ros.actions import Node
from std_msgs.msg import String


@pytest.mark.launch_test
def generate_test_description():
    baseline_node = Node(
        package="ai_robot_cpp_example",
        executable="baseline_node",
        output="screen",
    )

    return (
        launch.LaunchDescription(
            [
                baseline_node,
                launch_testing.actions.ReadyToTest(),
                launch.actions.TimerAction(
                    period=10.0,
                    actions=[
                        launch.actions.EmitEvent(event=launch.events.Shutdown())
                    ],
                ),
            ]
        ),
        {"baseline_node": baseline_node},
    )


class TestBaselineNodeEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_baseline_node_end_to_end")
        self.received = []
        self.subscription = self.node.create_subscription(
            String,
            "/robot_status",
            self.received.append,
            rclpy.qos.QoSProfile(
                depth=1,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
            ),
        )

    def tearDown(self):
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=3.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            if predicate():
                return True
        return False

    def test_process_publishes_ready_status(self):
        publisher_connected = self._spin_until(
            lambda: self.node.count_publishers("/robot_status") > 0,
            timeout=3.0,
        )
        self.assertTrue(
            publisher_connected,
            "baseline_node process did not publish /robot_status",
        )

        received_ready = self._spin_until(
            lambda: any(message.data == "ready" for message in self.received),
            timeout=3.0,
        )
        self.assertTrue(
            received_ready,
            "did not receive ready on /robot_status from baseline_node process",
        )


@launch_testing.post_shutdown_test()
class TestBaselineNodeShutdown(unittest.TestCase):
    def test_baseline_node_exits_cleanly(self, proc_info, baseline_node):
        launch_testing.asserts.assertExitCodes(proc_info, process=baseline_node)
