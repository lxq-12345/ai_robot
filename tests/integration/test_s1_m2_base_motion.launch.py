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


LEFT_WHEEL_JOINTS = ("left_front_wheel_joint", "left_rear_wheel_joint")
RIGHT_WHEEL_JOINTS = ("right_front_wheel_joint", "right_rear_wheel_joint")


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

    def _latest_side_wheel_velocities(self):
        for message in reversed(self.joint_state_messages):
            names = list(message.name)
            required = LEFT_WHEEL_JOINTS + RIGHT_WHEEL_JOINTS
            if all(joint in names for joint in required):
                indexes = {joint: names.index(joint) for joint in required}
                if len(message.velocity) > max(indexes.values()):
                    left = [message.velocity[indexes[joint]] for joint in LEFT_WHEEL_JOINTS]
                    right = [message.velocity[indexes[joint]] for joint in RIGHT_WHEEL_JOINTS]
                    return left, right
        return None

    def _wheel_groups_are_turning_in_opposite_directions(self):
        wheel_groups = self._latest_side_wheel_velocities()
        if wheel_groups is None:
            return False

        left, right = wheel_groups
        return (
            all(abs(value) > 0.5 for value in left + right)
            and all(value * left[0] > 0.0 for value in left)
            and all(value * right[0] > 0.0 for value in right)
            and left[0] * right[0] < 0.0
        )

    def _wheels_are_stopped(self):
        wheel_groups = self._latest_side_wheel_velocities()
        if wheel_groups is None:
            return False
        return all(abs(value) < 0.2 for side in wheel_groups for value in side)

    def _publish_command_for(self, linear_x=0.0, angular_z=0.0, duration=1.0):
        command = Twist()
        command.linear.x = linear_x
        command.angular.z = angular_z
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            self.publisher.publish(command)
            rclpy.spin_once(self.node, timeout_sec=0.05)

    def _publish_until(self, predicate, linear_x=0.0, angular_z=0.0, timeout=4.0):
        command = Twist()
        command.linear.x = linear_x
        command.angular.z = angular_z
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.publisher.publish(command)
            rclpy.spin_once(self.node, timeout_sec=0.05)
            if predicate():
                return True
        return False

    def test_base_moves_forward_backward_turns_and_stops(self):
        self.assertTrue(
            self._spin_until(lambda: len(self.odom_messages) >= 3),
            "simulation did not publish initial /odom messages",
        )
        self.assertTrue(
            self._spin_until(lambda: self._latest_side_wheel_velocities() is not None),
            "simulation did not publish wheel joint states",
        )

        start_x = self._latest_x()
        wheels_forward = self._publish_until(
            lambda: self._latest_side_wheel_velocities() is not None
            and all(value > 0.5 for side in self._latest_side_wheel_velocities() for value in side),
            linear_x=0.20,
            timeout=4.0,
        )
        self.assertTrue(wheels_forward, "forward command did not produce positive wheel speeds")

        moved_forward = self._publish_until(
            lambda: self._latest_x() > start_x + 0.03,
            linear_x=0.20,
            timeout=8.0,
        )
        self.assertTrue(moved_forward, "forward command did not increase odometry x")
        self.assertTrue(
            self._publish_until(self._wheels_are_stopped, timeout=4.0),
            "base did not settle after forward motion",
        )

        forward_x = self._latest_x()
        wheels_backward = self._publish_until(
            lambda: self._latest_side_wheel_velocities() is not None
            and all(value < -0.5 for side in self._latest_side_wheel_velocities() for value in side),
            linear_x=-0.20,
            timeout=4.0,
        )
        self.assertTrue(wheels_backward, "backward command did not produce negative wheel speeds")

        moved_backward = self._publish_until(
            lambda: self._latest_x() < forward_x - 0.03,
            linear_x=-0.20,
            timeout=8.0,
        )
        self.assertTrue(moved_backward, "backward command did not decrease odometry x")
        self.assertTrue(
            self._publish_until(self._wheels_are_stopped, timeout=4.0),
            "base did not settle after backward motion",
        )

        start_yaw = self._latest_yaw()
        wheels_turning = self._publish_until(
            self._wheel_groups_are_turning_in_opposite_directions,
            angular_z=0.60,
            timeout=4.0,
        )
        self.assertTrue(
            wheels_turning,
            f"turn command did not produce opposite wheel speeds: {self._latest_side_wheel_velocities()}",
        )

        turned = self._publish_until(
            lambda: abs(self._latest_yaw() - start_yaw) > 0.10,
            angular_z=0.60,
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
