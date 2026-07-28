import time
import unittest

import launch
import launch.actions
import launch.launch_description_sources
import launch_testing
import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from tf2_msgs.msg import TFMessage


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    bringup = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/sim_bringup.launch.py"
        )
    )

    return launch.LaunchDescription(
        [
            bringup,
            launch_testing.actions.ReadyToTest(),
        ]
    ), {}


class TestS1M4MotionSafetyIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_s1_m4_motion_safety_integration")
        self.cmd_vel_messages = []
        self.odom_messages = []
        self.joint_state_messages = []
        self.tf_messages = []
        self.publisher = self.node.create_publisher(Twist, "/cmd_vel_raw", 10)
        self.node.create_subscription(Twist, "/cmd_vel", self.cmd_vel_messages.append, 10)
        self.node.create_subscription(Odometry, "/odom", self.odom_messages.append, 10)
        self.node.create_subscription(JointState, "/joint_states", self.joint_state_messages.append, 10)
        self.node.create_subscription(TFMessage, "/tf", self.tf_messages.append, 10)

    def tearDown(self):
        stop = Twist()
        for _ in range(5):
            self.publisher.publish(stop)
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=12.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.10)
            if predicate():
                return True
        return False

    def _latest_wheel_velocities(self):
        for message in reversed(self.joint_state_messages):
            names = list(message.name)
            if "left_wheel_joint" in names and "right_wheel_joint" in names:
                left_index = names.index("left_wheel_joint")
                right_index = names.index("right_wheel_joint")
                if len(message.velocity) > max(left_index, right_index):
                    return message.velocity[left_index], message.velocity[right_index]
        return None

    def _has_odom_to_base_tf(self):
        for message in self.tf_messages:
            for transform in message.transforms:
                if transform.header.frame_id == "odom" and transform.child_frame_id == "base_link":
                    return True
        return False

    def test_base_encoder_odom_tf_and_timeout_stop_chain(self):
        self.assertTrue(self._spin_until(lambda: self.odom_messages), "missing /odom")
        self.assertTrue(
            self._spin_until(lambda: self._latest_wheel_velocities() is not None),
            "missing wheel encoder joint states",
        )
        self.assertTrue(self._spin_until(self._has_odom_to_base_tf), "missing odom -> base_link TF")

        start_x = self.odom_messages[-1].pose.pose.position.x
        command = Twist()
        command.linear.x = 1.0
        self.publisher.publish(command)

        self.assertTrue(
            self._spin_until(lambda: any(abs(msg.linear.x - 0.35) < 1e-6 for msg in self.cmd_vel_messages)),
            "cmd_vel_guard did not limit raw velocity before the base",
        )
        self.assertTrue(
            self._spin_until(
                lambda: self._latest_wheel_velocities() is not None
                and self._latest_wheel_velocities()[0] > 0.5
                and self._latest_wheel_velocities()[1] > 0.5
            ),
            "encoder joint speeds did not reflect forward motion",
        )
        self.assertTrue(
            self._spin_until(lambda: self.odom_messages[-1].pose.pose.position.x > start_x + 0.03),
            "odometry did not advance after bounded velocity command",
        )

        self.cmd_vel_messages.clear()
        self.assertTrue(
            self._spin_until(lambda: any(abs(msg.linear.x) < 1e-6 for msg in self.cmd_vel_messages), timeout=2.0),
            "cmd_vel_guard did not publish stop after raw command timeout",
        )
        self.assertTrue(
            self._spin_until(lambda: abs(self.odom_messages[-1].twist.twist.linear.x) < 0.03, timeout=4.0),
            "base odometry did not settle after safety timeout stop",
        )
