import time
import unittest

import launch
import launch_ros.actions
import launch_testing
import rclpy
from geometry_msgs.msg import Twist


def generate_test_description():
    guard = launch_ros.actions.Node(
        package="ai_robot_sim",
        executable="cmd_vel_guard",
        parameters=[
            {
                "max_linear_speed": 0.30,
                "max_angular_speed": 0.80,
                "command_timeout": 0.20,
            }
        ],
        output="screen",
    )

    return launch.LaunchDescription(
        [
            guard,
            launch_testing.actions.ReadyToTest(),
        ]
    ), {"guard": guard}


class TestCmdVelGuardLaunch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_cmd_vel_guard")
        self.received = []
        self.publisher = self.node.create_publisher(Twist, "/cmd_vel_raw", 10)
        self.subscription = self.node.create_subscription(
            Twist,
            "/cmd_vel",
            self.received.append,
            10,
        )
        self.assertTrue(self._wait_for_graph(), "cmd_vel_guard topics did not connect")

    def tearDown(self):
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            if predicate():
                return True
        return False

    def _wait_for_graph(self):
        return self._spin_until(
            lambda: self.publisher.get_subscription_count() > 0
            and self.node.count_publishers("/cmd_vel") > 0,
            timeout=3.0,
        )

    def _publish_raw(self, command, count=5):
        for _ in range(count):
            self.publisher.publish(command)
            rclpy.spin_once(self.node, timeout_sec=0.05)

    def test_raw_velocity_is_limited(self):
        command = Twist()
        command.linear.x = 1.00
        command.angular.z = -1.50

        self.received.clear()
        self._publish_raw(command)

        received_limited = self._spin_until(
            lambda: any(
                abs(msg.linear.x - 0.30) < 1e-6
                and abs(msg.angular.z + 0.80) < 1e-6
                for msg in self.received
            )
        )
        self.assertTrue(received_limited, "cmd_vel_guard did not publish limited velocity")

    def test_timeout_publishes_stop_command(self):
        command = Twist()
        command.linear.x = 0.20
        command.angular.z = 0.30

        self.received.clear()
        self._publish_raw(command)

        received_motion = self._spin_until(
            lambda: any(abs(msg.linear.x - 0.20) < 1e-6 for msg in self.received)
        )
        self.assertTrue(received_motion, "cmd_vel_guard did not forward valid velocity")
        self.received.clear()

        received_stop = self._spin_until(
            lambda: any(
                abs(msg.linear.x) < 1e-6
                and abs(msg.angular.z) < 1e-6
                for msg in self.received
            ),
            timeout=2.0,
        )
        self.assertTrue(received_stop, "cmd_vel_guard did not publish stop after timeout")


@launch_testing.post_shutdown_test()
class TestCmdVelGuardShutdown(unittest.TestCase):
    def test_guard_exits_cleanly(self, proc_info, guard):
        launch_testing.asserts.assertExitCodes(proc_info, process=guard)
