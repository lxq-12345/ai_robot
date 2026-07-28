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
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped, Twist
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import Odometry
from nav2_msgs.action import ComputePathToPose, NavigateToPose
from rclpy.action import ActionClient
from tf2_msgs.msg import TFMessage


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    nav2 = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/nav2_bringup.launch.py"
        )
    )
    return launch.LaunchDescription([nav2, launch_testing.actions.ReadyToTest()]), {}


class TestS1M5Nav2(unittest.TestCase):
    @classmethod
    def setUpClass(cls): rclpy.init()
    @classmethod
    def tearDownClass(cls): rclpy.shutdown()
    def setUp(self):
        self.node = rclpy.create_node("test_s1_m5_nav2")
        self.initial_pose = self.node.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)
        self.client = ActionClient(self.node, NavigateToPose, "/navigate_to_pose")
        self.planner_client = ActionClient(self.node, ComputePathToPose, "/compute_path_to_pose")
        self.odom_messages = []
        self.transforms = []
        self.raw_commands = []
        self.bounded_commands = []
        self.node.create_subscription(Odometry, "/odom", self.odom_messages.append, 10)
        self.node.create_subscription(TFMessage, "/tf", self.transforms.append, 10)
        self.node.create_subscription(Twist, "/cmd_vel_raw", self.raw_commands.append, 10)
        self.node.create_subscription(Twist, "/cmd_vel", self.bounded_commands.append, 10)
        self.controller_state = self.node.create_client(GetState, "/controller_server/get_state")
        self.navigator_state = self.node.create_client(GetState, "/bt_navigator/get_state")
        self.waypoint_state = self.node.create_client(GetState, "/waypoint_follower/get_state")
        self.smoother_state = self.node.create_client(GetState, "/velocity_smoother/get_state")
    def tearDown(self): self.node.destroy_node()
    def _spin_until(self, predicate, timeout=30.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if predicate(): return True
        return False
    def _controller_is_active(self):
        future = self.controller_state.call_async(GetState.Request())
        if not self._spin_until(lambda: future.done(), timeout=2.0):
            return False
        return future.result().current_state.id == State.PRIMARY_STATE_ACTIVE
    def _navigator_is_active(self):
        if not self.navigator_state.wait_for_service(timeout_sec=0.1): return False
        future = self.navigator_state.call_async(GetState.Request())
        if not self._spin_until(lambda: future.done(), timeout=2.0): return False
        return future.result().current_state.id == State.PRIMARY_STATE_ACTIVE
    def _waypoint_is_active(self):
        if not self.waypoint_state.wait_for_service(timeout_sec=0.1): return False
        future = self.waypoint_state.call_async(GetState.Request())
        if not self._spin_until(lambda: future.done(), timeout=2.0): return False
        return future.result().current_state.id == State.PRIMARY_STATE_ACTIVE
    def _smoother_is_active(self):
        if not self.smoother_state.wait_for_service(timeout_sec=0.1): return False
        future = self.smoother_state.call_async(GetState.Request())
        if not self._spin_until(lambda: future.done(), timeout=2.0): return False
        return future.result().current_state.id == State.PRIMARY_STATE_ACTIVE
    def _send_goal(self, x, y):
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = "map"
        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y
        goal.pose.pose.orientation.w = 1.0
        future = self.client.send_goal_async(goal)
        self.assertTrue(self._spin_until(lambda: future.done()), "goal request timed out")
        goal_handle = future.result()
        self.assertTrue(goal_handle.accepted, "Nav2 rejected reachable goal")
        return goal_handle
    def test_nav2_accepts_a_goal_after_localization(self):
        self.assertTrue(self._spin_until(lambda: self.odom_messages), "Gazebo odometry unavailable")
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.068
        for _ in range(5):
            self.initial_pose.publish(pose)
            rclpy.spin_once(self.node, timeout_sec=0.1)
        self.assertTrue(self._spin_until(lambda: any(t.header.frame_id == "map" and t.child_frame_id == "odom" for m in self.transforms for t in m.transforms)), "AMCL did not publish map -> odom")
        self.assertTrue(self.controller_state.wait_for_service(timeout_sec=20.0), "controller lifecycle service unavailable")
        self.assertTrue(self._spin_until(self._controller_is_active, timeout=30.0), "controller server did not become active")
        self.assertTrue(self._spin_until(self._navigator_is_active, timeout=30.0), "BT navigator did not become active")
        self.assertTrue(self._spin_until(self._waypoint_is_active, timeout=30.0), "waypoint follower did not become active")
        self.assertTrue(self._spin_until(self._smoother_is_active, timeout=30.0), "velocity smoother did not become active")
        self.assertTrue(self.client.wait_for_server(timeout_sec=30.0), "NavigateToPose server unavailable")
        goal_handle = self._send_goal(2.0, -1.0)
        cancel_future = goal_handle.cancel_goal_async()
        self.assertTrue(self._spin_until(lambda: cancel_future.done(), timeout=10.0), "goal cancellation timed out")
        self.assertTrue(cancel_future.result().goals_canceling, "Nav2 did not accept goal cancellation")
        result_future = goal_handle.get_result_async()
        self.assertTrue(self._spin_until(lambda: result_future.done(), timeout=20.0), "cancelled goal did not finish")
        self.assertEqual(result_future.result().status, GoalStatus.STATUS_CANCELED, "goal did not reach cancelled state")
    def test_nav2_reaches_fixed_route_through_safety_guard(self):
        self.assertTrue(self._spin_until(lambda: self.odom_messages), "Gazebo odometry unavailable")
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.068
        for _ in range(5):
            self.initial_pose.publish(pose)
            rclpy.spin_once(self.node, timeout_sec=0.1)
        self.assertTrue(self._spin_until(self._smoother_is_active, timeout=30.0), "navigation stack did not become active")
        self.assertTrue(self.client.wait_for_server(timeout_sec=30.0), "NavigateToPose server unavailable")
        for x, y in ((-0.5, -0.3), (-0.5, 0.3)):
            result_future = self._send_goal(x, y).get_result_async()
            self.assertTrue(self._spin_until(lambda: result_future.done(), timeout=75.0), "fixed-route goal timed out")
            self.assertEqual(result_future.result().status, GoalStatus.STATUS_SUCCEEDED, "fixed-route goal did not succeed")
        self.assertTrue(any(abs(command.linear.x) > 0.01 for command in self.raw_commands), "Nav2 did not publish raw velocity commands")
        self.assertTrue(any(abs(command.linear.x) > 0.01 for command in self.bounded_commands), "safety guard did not forward Nav2 commands")
        self.assertTrue(all(abs(command.linear.x) <= 0.35 + 1e-6 for command in self.bounded_commands), "safety guard exceeded linear speed limit")
    def test_global_planner_routes_around_static_obstacle(self):
        self.assertTrue(self._spin_until(lambda: self.odom_messages), "Gazebo odometry unavailable")
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.068
        for _ in range(5):
            self.initial_pose.publish(pose)
            rclpy.spin_once(self.node, timeout_sec=0.1)
        self.assertTrue(self._spin_until(self._smoother_is_active, timeout=30.0), "navigation stack did not become active")
        self.assertTrue(self.planner_client.wait_for_server(timeout_sec=30.0), "ComputePathToPose server unavailable")
        request = ComputePathToPose.Goal()
        request.goal.header.frame_id = "map"
        request.goal.pose.position.x = 2.0
        request.goal.pose.position.y = 1.0
        request.goal.pose.orientation.w = 1.0
        request.use_start = False
        future = self.planner_client.send_goal_async(request)
        self.assertTrue(self._spin_until(lambda: future.done()), "planner request timed out")
        goal_handle = future.result()
        self.assertTrue(goal_handle.accepted, "planner rejected obstacle-route request")
        result_future = goal_handle.get_result_async()
        self.assertTrue(self._spin_until(lambda: result_future.done(), timeout=20.0), "planner result timed out")
        path = result_future.result().result.path.poses
        self.assertGreater(len(path), 2, "planner returned no path around static obstacle")
        self.assertFalse(
            any(0.5 <= point.pose.position.x <= 1.5 and 0.0 <= point.pose.position.y <= 1.5 for point in path),
            "global path crosses the static obstacle footprint",
        )

    def test_global_planner_rejects_goal_inside_static_obstacle(self):
        self.assertTrue(self._spin_until(lambda: self.odom_messages), "Gazebo odometry unavailable")
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.068
        for _ in range(5):
            self.initial_pose.publish(pose)
            rclpy.spin_once(self.node, timeout_sec=0.1)
        self.assertTrue(self._spin_until(self._smoother_is_active, timeout=30.0), "navigation stack did not become active")
        self.assertTrue(self.planner_client.wait_for_server(timeout_sec=30.0), "ComputePathToPose server unavailable")
        request = ComputePathToPose.Goal()
        request.goal.header.frame_id = "map"
        request.goal.pose.position.x = 1.0
        request.goal.pose.position.y = 0.7
        request.goal.pose.orientation.w = 1.0
        request.use_start = False
        future = self.planner_client.send_goal_async(request)
        self.assertTrue(self._spin_until(lambda: future.done()), "unreachable planner request timed out")
        goal_handle = future.result()
        self.assertTrue(goal_handle.accepted, "planner did not accept unreachable request for evaluation")
        result_future = goal_handle.get_result_async()
        self.assertTrue(self._spin_until(lambda: result_future.done(), timeout=20.0), "unreachable planner result timed out")
        result = result_future.result()
        self.assertEqual(result.status, GoalStatus.STATUS_SUCCEEDED, "planner action did not return a result")
        self.assertTrue(result.result.path.poses, "planner returned no diagnostic path for the obstacle goal")
        endpoint = result.result.path.poses[-1].pose.position
        self.assertGreater(
            hypot(endpoint.x - 1.0, endpoint.y - 0.7),
            0.35,
            "planner treated a goal inside the static obstacle as reachable",
        )
