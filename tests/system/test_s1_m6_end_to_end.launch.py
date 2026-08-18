import math
import time
import unittest

import launch
import launch.actions
import launch.launch_description_sources
import launch_ros.actions
import launch_testing
import rclpy
from action_msgs.msg import GoalStatus
from ai_robot_interfaces.action import ExecuteCapabilityTask
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from tf2_msgs.msg import TFMessage


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    bringup = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/nav2_bringup.launch.py"
        )
    )
    task_manager = launch_ros.actions.Node(
        package="ai_robot_sim",
        executable="capability_task_manager",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )
    return launch.LaunchDescription(
        [bringup, task_manager, launch_testing.actions.ReadyToTest()]
    ), {"task_manager": task_manager}


class TestS1M6EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_s1_m6_end_to_end")
        self.client = ActionClient(
            self.node,
            ExecuteCapabilityTask,
            "/execute_capability_task",
        )
        self.initial_pose = self.node.create_publisher(
            PoseWithCovarianceStamped, "/initialpose", 10
        )
        self.odom = []
        self.transforms = []
        self.raw_commands = []
        self.safe_commands = []
        self.feedback_phases = []
        self.node.create_subscription(
            Odometry, "/odom", self.odom.append, 10
        )
        self.node.create_subscription(
            TFMessage, "/tf", self.transforms.append, 10
        )
        self.node.create_subscription(
            Twist, "/cmd_vel_raw", self.raw_commands.append, 10
        )
        self.node.create_subscription(
            Twist, "/cmd_vel", self.safe_commands.append, 10
        )
        self.smoother_state = self.node.create_client(
            GetState, "/velocity_smoother/get_state"
        )

    def tearDown(self):
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=30.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.10)
            if predicate():
                return True
        return False

    def _smoother_is_active(self):
        if not self.smoother_state.wait_for_service(timeout_sec=0.1):
            return False
        future = self.smoother_state.call_async(GetState.Request())
        if not self._spin_until(future.done, timeout=2.0):
            return False
        return (
            future.result().current_state.id
            == State.PRIMARY_STATE_ACTIVE
        )

    def _publish_initial_pose(self):
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = 0.25
        pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.068
        for _ in range(6):
            self.initial_pose.publish(pose)
            rclpy.spin_once(self.node, timeout_sec=0.10)

    def _make_goal(self):
        goal = ExecuteCapabilityTask.Goal()
        goal.task_id = "m6-real-nav-observe"
        goal.capability = "navigate_and_observe"
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.pose.position.x = -0.5
        goal.target_pose.pose.position.y = -0.3
        goal.target_pose.pose.orientation.w = 1.0
        goal.timeout_sec = 60.0
        goal.require_scan = True
        goal.require_image = True
        return goal

    def _on_feedback(self, feedback_message):
        self.feedback_phases.append(feedback_message.feedback.phase)

    def _send_goal(self, goal, feedback=False):
        callback = self._on_feedback if feedback else None
        future = self.client.send_goal_async(
            goal, feedback_callback=callback
        )
        self.assertTrue(
            self._spin_until(future.done, timeout=5.0),
            "capability goal response timed out",
        )
        handle = future.result()
        self.assertTrue(handle.accepted, "capability task was rejected")
        return handle

    def test_real_nav2_task_navigates_perceives_and_replays(self):
        self.assertTrue(
            self._spin_until(lambda: self.odom),
            "Gazebo odometry unavailable",
        )
        self._publish_initial_pose()

        def map_to_odom():
            return any(
                transform.header.frame_id == "map"
                and transform.child_frame_id == "odom"
                for message in self.transforms
                for transform in message.transforms
            )

        self.assertTrue(
            self._spin_until(map_to_odom),
            "AMCL did not publish map to odom",
        )
        self.assertTrue(
            self._spin_until(self._smoother_is_active, timeout=35.0),
            "Nav2 did not become active",
        )
        self.assertTrue(
            self.client.wait_for_server(timeout_sec=5.0),
            "capability task server unavailable",
        )

        start = time.monotonic()
        handle = self._send_goal(self._make_goal(), feedback=True)
        result_future = handle.get_result_async()
        self.assertTrue(
            self._spin_until(result_future.done, timeout=70.0),
            "integrated capability task timed out",
        )
        response = result_future.result()
        self.assertEqual(response.status, GoalStatus.STATUS_SUCCEEDED)
        self.assertEqual(
            response.result.outcome,
            ExecuteCapabilityTask.Result.SUCCEEDED,
        )
        self.assertFalse(response.result.replayed)
        self.assertTrue(math.isfinite(response.result.minimum_scan_range))
        self.assertGreater(response.result.minimum_scan_range, 0.0)
        self.assertGreater(response.result.image_width, 0)
        self.assertGreater(response.result.image_height, 0)
        self.assertIn(
            ExecuteCapabilityTask.Feedback.NAVIGATING,
            self.feedback_phases,
        )
        self.assertIn(
            ExecuteCapabilityTask.Feedback.PERCEIVING,
            self.feedback_phases,
        )
        self.assertTrue(
            any(abs(command.linear.x) > 0.01 for command in self.raw_commands),
            "Nav2 did not command motion",
        )
        self.assertTrue(
            any(abs(command.linear.x) > 0.01 for command in self.safe_commands),
            "safety guard did not forward motion",
        )
        self.assertTrue(
            all(
                abs(command.linear.x) <= 0.35 + 1e-6
                for command in self.safe_commands
            ),
            "safe velocity exceeded the frozen limit",
        )

        raw_count = len(self.raw_commands)
        replay_start = time.monotonic()
        replay_handle = self._send_goal(self._make_goal())
        replay_future = replay_handle.get_result_async()
        self.assertTrue(
            self._spin_until(replay_future.done, timeout=2.0),
            "idempotent replay timed out",
        )
        replay = replay_future.result()
        self.assertEqual(replay.status, GoalStatus.STATUS_SUCCEEDED)
        self.assertTrue(replay.result.replayed)
        self.assertLess(time.monotonic() - replay_start, 1.0)
        self.assertLessEqual(len(self.raw_commands) - raw_count, 2)
        self.assertLess(time.monotonic() - start, 70.0)


@launch_testing.post_shutdown_test()
class TestS1M6EndToEndShutdown(unittest.TestCase):
    def test_task_manager_exits_cleanly(
        self, proc_info, task_manager
    ):
        launch_testing.asserts.assertExitCodes(
            proc_info, process=task_manager
        )
