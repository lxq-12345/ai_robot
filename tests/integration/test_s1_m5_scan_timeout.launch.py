import time
import unittest

import launch
import launch_ros.actions
import launch_testing
import rclpy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan


def generate_test_description():
    guard = launch_ros.actions.Node(
        package="ai_robot_sim",
        executable="cmd_vel_guard",
        parameters=[
            {
                "require_scan": True,
                "scan_timeout": 0.20,
                "command_timeout": 1.0,
            }
        ],
        output="screen",
    )
    return launch.LaunchDescription(
        [guard, launch_testing.actions.ReadyToTest()]
    ), {"guard": guard}


class TestS1M5ScanTimeout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_s1_m5_scan_timeout")
        self.received = []
        self.command = self.node.create_publisher(Twist, "/cmd_vel_raw", 10)
        self.scan = self.node.create_publisher(LaserScan, "/scan", 10)
        self.node.create_subscription(Twist, "/cmd_vel", self.received.append, 10)

    def tearDown(self):
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            if predicate():
                return True
        return False

    def _publish_fresh_motion_until_received(self, timeout=2.0):
        command = Twist()
        command.linear.x = 0.20
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.scan.publish(LaserScan())
            rclpy.spin_once(self.node, timeout_sec=0.02)
            self.command.publish(command)
            rclpy.spin_once(self.node, timeout_sec=0.02)
            if any(message.linear.x > 0.1 for message in self.received):
                return True
        return False

    def test_stale_scan_forces_stop(self):
        graph_ready = self._spin_until(
            lambda: self.command.get_subscription_count() > 0
            and self.scan.get_subscription_count() > 0
            and self.node.count_publishers("/cmd_vel") > 0
        )
        self.assertTrue(graph_ready, "guard topics did not connect")
        self.assertTrue(
            self._publish_fresh_motion_until_received(),
            "fresh scan did not permit motion",
        )
        self.received.clear()
        stopped = self._spin_until(
            lambda: any(abs(message.linear.x) < 1e-6 for message in self.received),
            timeout=1.0,
        )
        self.assertTrue(stopped, "stale scan did not force stop")


@launch_testing.post_shutdown_test()
class TestShutdown(unittest.TestCase):
    def test_guard_exits_cleanly(self, proc_info, guard):
        launch_testing.asserts.assertExitCodes(proc_info, process=guard)
