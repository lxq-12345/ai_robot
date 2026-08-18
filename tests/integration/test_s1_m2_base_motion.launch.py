import math
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


class TestSimBaseMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_sim_base_motion")
        self.odom_messages = []
        self.joint_state_messages = []
        self.publisher = self.node.create_publisher(Twist, "/cmd_vel_raw", 10)
        self.subscription = self.node.create_subscription(
            Odometry,
            "/odom",
            self.odom_messages.append,
            10,
        )
        self.joint_state_subscription = self.node.create_subscription(
            JointState,
            "/joint_states",
            self.joint_state_messages.append,
            10,
        )

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

    def _latest_x(self):
        return self.odom_messages[-1].pose.pose.position.x

    def _latest_yaw(self):
        orientation = self.odom_messages[-1].pose.pose.orientation
        siny_cosp = 2.0 * (orientation.w * orientation.z + orientation.x * orientation.y)
        cosy_cosp = 1.0 - 2.0 * (orientation.y * orientation.y + orientation.z * orientation.z)
        return math.atan2(siny_cosp, cosy_cosp)

    def _latest_wheel_velocities(self):
        for message in reversed(self.joint_state_messages):
            names = list(message.name)
            if "left_wheel_joint" in names and "right_wheel_joint" in names:
                left_index = names.index("left_wheel_joint")
                right_index = names.index("right_wheel_joint")
                if len(message.velocity) > max(left_index, right_index):
                    return message.velocity[left_index], message.velocity[right_index]
        return None

    def _publish_command_for(self, linear_x=0.0, angular_z=0.0, duration=1.0):
        command = Twist()
        command.linear.x = linear_x
        command.angular.z = angular_z
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            self.publisher.publish(command)
            rclpy.spin_once(self.node, timeout_sec=0.05)

    def test_base_moves_forward_backward_turns_and_stops(self):
        self.assertTrue(
            self._spin_until(lambda: len(self.odom_messages) >= 3),
            "simulation did not publish initial /odom messages",
        )
        self.assertTrue(
            self._spin_until(lambda: self._latest_wheel_velocities() is not None),
            "simulation did not publish wheel joint states",
        )

        start_x = self._latest_x()
        self._publish_command_for(linear_x=0.20, duration=1.0)

        wheels_forward = self._spin_until(
            lambda: self._latest_wheel_velocities() is not None
            and self._latest_wheel_velocities()[0] > 0.5
            and self._latest_wheel_velocities()[1] > 0.5,
            timeout=4.0,
        )
        self.assertTrue(wheels_forward, "forward command did not produce positive wheel speeds")

        moved_forward = self._spin_until(
            lambda: self._latest_x() > start_x + 0.03,
            timeout=8.0,
        )
        self.assertTrue(moved_forward, "forward command did not increase odometry x")

        forward_x = self._latest_x()
        self._publish_command_for(linear_x=-0.20, duration=1.0)
        wheels_backward = self._spin_until(
            lambda: self._latest_wheel_velocities() is not None
            and self._latest_wheel_velocities()[0] < -0.5
            and self._latest_wheel_velocities()[1] < -0.5,
            timeout=4.0,
        )
        self.assertTrue(wheels_backward, "backward command did not produce negative wheel speeds")

        moved_backward = self._spin_until(
            lambda: self._latest_x() < forward_x - 0.03,
            timeout=8.0,
        )
        self.assertTrue(moved_backward, "backward command did not decrease odometry x")

        start_yaw = self._latest_yaw()
        self._publish_command_for(angular_z=0.60, duration=1.0)
        wheels_turning = self._spin_until(
            lambda: self._latest_wheel_velocities() is not None
            and self._latest_wheel_velocities()[0] * self._latest_wheel_velocities()[1] < 0.0,
            timeout=4.0,
        )
        self.assertTrue(wheels_turning, "turn command did not produce opposite wheel speeds")

        turned = self._spin_until(
            lambda: abs(self._latest_yaw() - start_yaw) > 0.10,
            timeout=8.0,
        )
        self.assertTrue(turned, "turn command did not change odometry yaw")

        stop = Twist()
        self.publisher.publish(stop)
        stopped = self._spin_until(
            lambda: abs(self.odom_messages[-1].twist.twist.linear.x) < 0.02,
            timeout=3.0,
        )
        self.assertTrue(stopped, "stop command was not reflected in odometry twist")
