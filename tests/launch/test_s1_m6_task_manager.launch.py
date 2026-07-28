import math
from pathlib import Path
import sys
import time
import unittest

import launch
import launch.actions
import launch_ros.actions
import launch_testing
import psutil
import rclpy
from action_msgs.msg import GoalStatus
from ai_robot_interfaces.action import ExecuteCapabilityTask
from rclpy.action import ActionClient
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import Bool, Int32, String


def generate_test_description():
    helper = Path(__file__).parents[1] / "helpers" / "fake_nav2_server.py"
    fake_nav2 = launch.actions.ExecuteProcess(
        cmd=[sys.executable, str(helper)],
        output="screen",
    )
    task_manager = launch_ros.actions.Node(
        package="ai_robot_sim",
        executable="capability_task_manager",
        parameters=[
            {
                "sensor_timeout": 0.30,
                "nav_server_timeout": 0.50,
                "maximum_cached_tasks": 8,
            }
        ],
        output="screen",
    )
    return launch.LaunchDescription(
        [fake_nav2, task_manager, launch_testing.actions.ReadyToTest()]
    ), {"fake_nav2": fake_nav2, "task_manager": task_manager}


class TestS1M6TaskManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_s1_m6_task_manager")
        self.client = ActionClient(
            self.node,
            ExecuteCapabilityTask,
            "/execute_capability_task",
        )
        self.mode = self.node.create_publisher(String, "/test/nav_mode", 10)
        self.scan = self.node.create_publisher(LaserScan, "/scan", 10)
        self.image = self.node.create_publisher(
            Image, "/camera/image_raw", 10
        )
        self.safety = self.node.create_publisher(Bool, "/safety_stop", 10)
        self.nav_counts = []
        self.node.create_subscription(
            Int32,
            "/test/nav_goal_count",
            lambda message: self.nav_counts.append(message.data),
            10,
        )
        self.assertTrue(
            self.client.wait_for_server(timeout_sec=3.0),
            "capability task action unavailable",
        )
        self.assertTrue(
            self._spin_until(
                lambda: self.mode.get_subscription_count() > 0
                and self.scan.get_subscription_count() > 0
                and self.image.get_subscription_count() > 0
                and self.safety.get_subscription_count() > 0
            ),
            "test graph did not connect",
        )
        self._publish_bool(False)
        self._set_mode("success")

    def tearDown(self):
        self._publish_bool(False)
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=3.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.02)
            if predicate():
                return True
        return False

    def _publish_bool(self, value):
        message = Bool()
        message.data = value
        for _ in range(3):
            self.safety.publish(message)
            rclpy.spin_once(self.node, timeout_sec=0.02)

    def _set_mode(self, mode):
        message = String()
        message.data = mode
        for _ in range(3):
            self.mode.publish(message)
            rclpy.spin_once(self.node, timeout_sec=0.02)

    def _publish_sensors(self):
        scan = LaserScan()
        scan.header.frame_id = "laser_link"
        scan.ranges = [1.2, 0.8, float("inf")]
        image = Image()
        image.header.frame_id = "camera_link"
        image.width = 320
        image.height = 240
        image.encoding = "mono8"
        image.step = 320
        image.data = [1] * (image.width * image.height)
        for _ in range(3):
            self.scan.publish(scan)
            self.image.publish(image)
            rclpy.spin_once(self.node, timeout_sec=0.03)

    def _goal(
        self,
        task_id,
        *,
        capability="navigate_and_observe",
        x=0.5,
        y=0.0,
        timeout=2.0,
        require_scan=False,
        require_image=False,
    ):
        goal = ExecuteCapabilityTask.Goal()
        goal.task_id = task_id
        goal.capability = capability
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        goal.target_pose.pose.orientation.w = 1.0
        goal.timeout_sec = timeout
        goal.require_scan = require_scan
        goal.require_image = require_image
        return goal

    def _send(self, goal, timeout=4.0):
        send_future = self.client.send_goal_async(goal)
        self.assertTrue(
            self._spin_until(send_future.done, timeout=timeout),
            "task goal response timed out",
        )
        handle = send_future.result()
        self.assertTrue(handle.accepted, "task goal rejected")
        result_future = handle.get_result_async()
        self.assertTrue(
            self._spin_until(result_future.done, timeout=timeout),
            "task result timed out",
        )
        return result_future.result()

    def _task_manager_rss(self):
        matches = []
        for process in psutil.process_iter(["cmdline", "memory_info"]):
            command = " ".join(process.info["cmdline"] or [])
            if "capability_task_manager" in command:
                matches.append(process.info["memory_info"].rss)
        self.assertTrue(matches, "task manager process not found")
        return max(matches)

    def test_invalid_and_out_of_bounds_tasks_are_reported(self):
        invalid = self._send(
            self._goal("invalid-capability", capability="unsupported")
        )
        self.assertEqual(
            invalid.result.outcome,
            ExecuteCapabilityTask.Result.INVALID_TASK,
        )
        self.assertEqual(invalid.status, GoalStatus.STATUS_ABORTED)

        bounds = self._send(self._goal("outside-map", x=8.0))
        self.assertEqual(
            bounds.result.outcome,
            ExecuteCapabilityTask.Result.OUT_OF_BOUNDS,
        )

    def test_navigation_failure_timeout_and_sensor_interruption(self):
        self._set_mode("fail")
        failed = self._send(self._goal("nav-failure"))
        self.assertEqual(
            failed.result.outcome,
            ExecuteCapabilityTask.Result.NAVIGATION_FAILED,
        )

        self._set_mode("hang")
        timed_out = self._send(
            self._goal("task-timeout", timeout=0.35),
            timeout=2.0,
        )
        self.assertEqual(
            timed_out.result.outcome,
            ExecuteCapabilityTask.Result.TIMED_OUT,
        )

        time.sleep(0.35)
        missing_sensor = self._send(
            self._goal("sensor-missing", require_image=True)
        )
        self.assertEqual(
            missing_sensor.result.outcome,
            ExecuteCapabilityTask.Result.SENSOR_UNAVAILABLE,
        )

    def test_cancel_busy_and_safety_trigger(self):
        self._set_mode("hang")
        first_future = self.client.send_goal_async(
            self._goal("busy-primary", timeout=3.0)
        )
        self.assertTrue(self._spin_until(first_future.done))
        first = first_future.result()
        self.assertTrue(first.accepted)

        second_future = self.client.send_goal_async(
            self._goal("busy-secondary")
        )
        self.assertTrue(self._spin_until(second_future.done))
        self.assertFalse(second_future.result().accepted)

        cancel_future = first.cancel_goal_async()
        self.assertTrue(self._spin_until(cancel_future.done))
        first_result = first.get_result_async()
        self.assertTrue(self._spin_until(first_result.done))
        self.assertEqual(
            first_result.result().result.outcome,
            ExecuteCapabilityTask.Result.CANCELED,
        )

        safety_future = self.client.send_goal_async(
            self._goal("safety-trigger", timeout=3.0)
        )
        self.assertTrue(self._spin_until(safety_future.done))
        safety_handle = safety_future.result()
        self.assertTrue(safety_handle.accepted)
        self._publish_bool(True)
        safety_result = safety_handle.get_result_async()
        self.assertTrue(self._spin_until(safety_result.done))
        self.assertEqual(
            safety_result.result().result.outcome,
            ExecuteCapabilityTask.Result.SAFETY_TRIGGERED,
        )

    def test_success_replay_and_bounded_resource_use(self):
        self._publish_sensors()
        first = self._send(
            self._goal(
                "normal-task",
                require_scan=True,
                require_image=True,
            )
        )
        self.assertEqual(
            first.result.outcome,
            ExecuteCapabilityTask.Result.SUCCEEDED,
        )
        self.assertFalse(first.result.replayed)
        self.assertAlmostEqual(first.result.minimum_scan_range, 0.8, places=3)
        self.assertEqual(first.result.image_width, 320)
        goal_count = self.nav_counts[-1]

        replay = self._send(
            self._goal(
                "normal-task",
                require_scan=True,
                require_image=True,
            )
        )
        self.assertTrue(replay.result.replayed)
        self.assertEqual(self.nav_counts[-1], goal_count)

        rss_before = self._task_manager_rss()
        for index in range(12):
            result = self._send(self._goal(f"resource-{index}"))
            self.assertEqual(
                result.result.outcome,
                ExecuteCapabilityTask.Result.SUCCEEDED,
            )
        rss_after = self._task_manager_rss()
        self.assertLess(rss_after, 200 * 1024 * 1024)
        self.assertLess(rss_after - rss_before, 30 * 1024 * 1024)
        self.assertTrue(math.isfinite(first.result.minimum_scan_range))


@launch_testing.post_shutdown_test()
class TestS1M6TaskManagerShutdown(unittest.TestCase):
    def test_processes_exit_cleanly(
        self, proc_info, fake_nav2, task_manager
    ):
        launch_testing.asserts.assertExitCodes(
            proc_info, process=fake_nav2
        )
        launch_testing.asserts.assertExitCodes(
            proc_info, process=task_manager
        )
