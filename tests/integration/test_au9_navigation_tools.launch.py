import time
import unittest
from math import hypot

import launch
import launch.actions
import launch.launch_description_sources
import launch_testing
import rclpy
from ament_index_python.packages import get_package_share_directory
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import Odometry
from nav2_msgs.action import FollowWaypoints, NavigateToPose
from rclpy.action import ActionClient
from sensor_msgs.msg import JointState
from tf2_msgs.msg import TFMessage


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    nav2 = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/apartment_nav2_bringup.launch.py"
        )
    )
    return launch.LaunchDescription(
        [nav2, launch_testing.actions.ReadyToTest()]
    ), {}


class TestAu9NavigationTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        if rclpy.ok():
            rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_au9_navigation_tools")
        self.initial_pose = self.node.create_publisher(
            PoseWithCovarianceStamped, "/initialpose", 10
        )
        self.navigate_client = ActionClient(
            self.node, NavigateToPose, "/navigate_to_pose"
        )
        self.waypoint_client = ActionClient(
            self.node, FollowWaypoints, "/follow_waypoints"
        )
        self.odom_messages = []
        self.transforms = []
        self.raw_commands = []
        self.safe_commands = []
        self.joint_states = []
        self.node.create_subscription(
            Odometry, "/odom", self.odom_messages.append, 10
        )
        self.node.create_subscription(
            TFMessage, "/tf", self.transforms.append, 10
        )
        self.node.create_subscription(
            Twist, "/cmd_vel_raw", self.raw_commands.append, 10
        )
        self.node.create_subscription(
            Twist, "/cmd_vel", self._on_safe_command, 10
        )
        self.node.create_subscription(
            JointState, "/joint_states", self.joint_states.append, 10
        )
        self.navigator_state = self.node.create_client(
            GetState, "/bt_navigator/get_state"
        )
        self.waypoint_state = self.node.create_client(
            GetState, "/waypoint_follower/get_state"
        )

    def tearDown(self):
        self.node.destroy_node()

    def _on_safe_command(self, command):
        self.safe_commands.append((time.monotonic(), command))

    def _spin_until(self, predicate, timeout=30.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if predicate():
                return True
        return False

    def _lifecycle_active(self, client):
        if not client.wait_for_service(timeout_sec=0.1):
            return False
        future = client.call_async(GetState.Request())
        if not self._spin_until(lambda: future.done(), timeout=2.0):
            return False
        return future.result().current_state.id == State.PRIMARY_STATE_ACTIVE

    def _pose(self, x, y):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.node.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.w = 1.0
        return pose

    def _publish_initial_pose(self):
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.position.x = 1.80
        pose.pose.pose.position.y = 4.00
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.068
        for _ in range(6):
            pose.header.stamp = self.node.get_clock().now().to_msg()
            self.initial_pose.publish(pose)
            rclpy.spin_once(self.node, timeout_sec=0.1)

    def _send_navigation_goal(self, x, y):
        goal = NavigateToPose.Goal()
        goal.pose = self._pose(x, y)
        future = self.navigate_client.send_goal_async(goal)
        self.assertTrue(
            self._spin_until(lambda: future.done()),
            "NavigateToPose request timed out",
        )
        handle = future.result()
        self.assertTrue(handle.accepted, "NavigateToPose goal was rejected")
        return handle

    @staticmethod
    def _moving(command):
        return abs(command.linear.x) > 0.01 or abs(command.angular.z) > 0.01

    @staticmethod
    def _joint_positions(message):
        return dict(zip(message.name, message.position))

    def _motion_diagnostics(self, start, start_wheels):
        current = self.odom_messages[-1] if self.odom_messages else None
        if current is None:
            odom_summary = "odom=missing"
        else:
            position = current.pose.pose.position
            distance = hypot(position.x - start.x, position.y - start.y)
            odom_summary = (
                f"odom=({position.x:.3f},{position.y:.3f}), "
                f"distance={distance:.3f}, "
                f"odom_v=({current.twist.twist.linear.x:.3f},"
                f"{current.twist.twist.angular.z:.3f})"
            )
        safe_messages = [command for _, command in self.safe_commands]
        max_raw_linear = max(
            (abs(command.linear.x) for command in self.raw_commands), default=0.0
        )
        max_raw_angular = max(
            (abs(command.angular.z) for command in self.raw_commands), default=0.0
        )
        max_safe_linear = max(
            (abs(command.linear.x) for command in safe_messages), default=0.0
        )
        max_safe_angular = max(
            (abs(command.angular.z) for command in safe_messages), default=0.0
        )
        wheel_summary = "wheels=missing"
        if self.joint_states:
            current_wheels = self._joint_positions(self.joint_states[-1])
            wheel_deltas = {
                name: current_wheels[name] - position
                for name, position in start_wheels.items()
                if name in current_wheels
            }
            wheel_summary = "wheel_delta={" + ",".join(
                f"{name}:{delta:.3f}" for name, delta in sorted(wheel_deltas.items())
            ) + "}"
        return (
            f"{odom_summary}, raw_count={len(self.raw_commands)}, "
            f"safe_count={len(safe_messages)}, "
            f"max_raw=({max_raw_linear:.3f},{max_raw_angular:.3f}), "
            f"max_safe=({max_safe_linear:.3f},{max_safe_angular:.3f}), "
            f"{wheel_summary}"
        )

    def test_au9_waypoints_cancel_stop_and_single_goal(self):
        self.assertTrue(
            self._spin_until(lambda: self.odom_messages, timeout=30.0),
            "Gazebo odometry unavailable",
        )
        self._publish_initial_pose()
        self.assertTrue(
            self._spin_until(
                lambda: any(
                    transform.header.frame_id == "map"
                    and transform.child_frame_id == "odom"
                    for message in self.transforms
                    for transform in message.transforms
                ),
                timeout=30.0,
            ),
            "AMCL did not publish map -> odom",
        )
        self.assertTrue(
            self._spin_until(
                lambda: self._lifecycle_active(self.navigator_state),
                timeout=30.0,
            ),
            "BT navigator did not become active",
        )
        self.assertTrue(
            self._spin_until(
                lambda: self._lifecycle_active(self.waypoint_state),
                timeout=30.0,
            ),
            "waypoint follower did not become active",
        )
        self.assertTrue(
            self.navigate_client.wait_for_server(timeout_sec=30.0),
            "NavigateToPose server unavailable",
        )
        self.assertTrue(
            self.waypoint_client.wait_for_server(timeout_sec=30.0),
            "FollowWaypoints server unavailable",
        )

        start = self.odom_messages[-1].pose.pose.position
        self.assertTrue(
            self._spin_until(lambda: self.joint_states, timeout=10.0),
            "wheel joint states unavailable",
        )
        start_wheels = self._joint_positions(self.joint_states[-1])
        waypoints = FollowWaypoints.Goal()
        waypoints.poses = [self._pose(1.50, 4.00), self._pose(1.20, 4.00)]
        request = self.waypoint_client.send_goal_async(waypoints)
        self.assertTrue(
            self._spin_until(lambda: request.done()),
            "FollowWaypoints request timed out",
        )
        waypoint_handle = request.result()
        self.assertTrue(waypoint_handle.accepted, "waypoint goal was rejected")
        waypoint_result = waypoint_handle.get_result_async()
        waypoint_finished = self._spin_until(
            lambda: waypoint_result.done(), timeout=120.0
        )
        self.assertTrue(
            waypoint_finished,
            "waypoint route timed out: "
            + self._motion_diagnostics(start, start_wheels),
        )
        self.assertEqual(
            waypoint_result.result().status,
            GoalStatus.STATUS_SUCCEEDED,
            "waypoint route did not succeed",
        )
        self.assertEqual(
            list(waypoint_result.result().result.missed_waypoints),
            [],
            "waypoint follower reported missed waypoints",
        )
        waypoint_end = self.odom_messages[-1].pose.pose.position
        self.assertGreater(
            hypot(waypoint_end.x - start.x, waypoint_end.y - start.y),
            0.35,
            "odometry did not show multi-waypoint movement",
        )

        motion_count = len(self.safe_commands)
        cancel_handle = self._send_navigation_goal(1.80, 5.80)
        self.assertTrue(
            self._spin_until(
                lambda: any(
                    self._moving(command)
                    for _, command in self.safe_commands[motion_count:]
                ),
                timeout=30.0,
            ),
            "robot did not begin moving before cancellation",
        )
        cancel_future = cancel_handle.cancel_goal_async()
        self.assertTrue(
            self._spin_until(lambda: cancel_future.done(), timeout=10.0),
            "goal cancellation timed out",
        )
        self.assertTrue(
            cancel_future.result().goals_canceling,
            "Nav2 did not accept cancellation",
        )
        cancel_result = cancel_handle.get_result_async()
        self.assertTrue(
            self._spin_until(lambda: cancel_result.done(), timeout=20.0),
            "cancelled goal did not finish",
        )
        self.assertEqual(
            cancel_result.result().status,
            GoalStatus.STATUS_CANCELED,
            "goal did not reach canceled state",
        )
        cancel_time = time.monotonic()
        self.assertTrue(
            self._spin_until(
                lambda: time.monotonic() >= cancel_time + 2.0,
                timeout=3.0,
            )
        )
        self.assertFalse(
            any(
                stamp > cancel_time + 0.5 and self._moving(command)
                for stamp, command in self.safe_commands
            ),
            "safe velocity remained non-zero after cancellation",
        )

        return_handle = self._send_navigation_goal(1.80, 4.00)
        return_result = return_handle.get_result_async()
        self.assertTrue(
            self._spin_until(lambda: return_result.done(), timeout=120.0),
            "single-goal return timed out",
        )
        self.assertEqual(
            return_result.result().status,
            GoalStatus.STATUS_SUCCEEDED,
            "single-goal navigation did not succeed",
        )

        self.assertTrue(
            any(self._moving(command) for command in self.raw_commands),
            "Nav2 did not publish raw velocity commands",
        )
        safe_messages = [command for _, command in self.safe_commands]
        self.assertTrue(
            any(self._moving(command) for command in safe_messages),
            "safety guard did not forward motion commands",
        )
        self.assertTrue(
            all(abs(command.linear.x) <= 0.35 + 1e-6 for command in safe_messages),
            "safety guard exceeded the linear speed limit",
        )
        self.assertTrue(
            all(abs(command.angular.z) <= 1.20 + 1e-6 for command in safe_messages),
            "safety guard exceeded the angular speed limit",
        )
