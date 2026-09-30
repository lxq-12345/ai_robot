"""Send a multi-room FollowWaypoints goal to an already running AU9 Nav2."""

import math
import time
import unittest

import launch
import launch_testing
import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import FollowWaypoints
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock


ROOM_WAYPOINTS = [
    ("主卧", 4.70, 5.35, math.pi / 2.0),
    ("小孩房", 5.20, 1.50, -math.pi / 2.0),
    ("起点", 1.80, 4.00, 0.0),
]
START = ("起点", 1.80, 4.00, 0.0)
READY_TIMEOUT_SEC = 12.0
REQUIRED_NODES = {
    "rviz": "RViz2",
    "amcl": "AMCL",
    "map_server": "Map Server",
    "bt_navigator": "Nav2 BT Navigator",
    "waypoint_follower": "Waypoint Follower",
}


def generate_test_description():
    # The Gazebo/Nav2 environment must already be running separately.
    keep_test_attached = launch.actions.TimerAction(period=420.0, actions=[])
    return launch.LaunchDescription(
        [launch_testing.actions.ReadyToTest(), keep_test_attached]
    ), {}


class TestAu9WaypointRooms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        if rclpy.ok():
            rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node(
            "test_au9_waypoint_rooms",
            parameter_overrides=[Parameter("use_sim_time", value=True)],
        )
        self.client = ActionClient(
            self.node, FollowWaypoints, "/follow_waypoints"
        )
        self.clock_seen = False
        self.clock_subscription = self.node.create_subscription(
            Clock, "/clock", self._on_clock, qos_profile_sensor_data
        )
        self.feedback_indices = []
        self.last_feedback_index = None

    def tearDown(self):
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if predicate():
                return True
        return False

    def _pose(self, x, y, yaw):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.node.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def _on_clock(self, _message):
        self.clock_seen = True

    def _on_waypoint_feedback(self, message):
        index = message.feedback.current_waypoint
        self.feedback_indices.append(index)
        if index == self.last_feedback_index or index >= len(ROOM_WAYPOINTS):
            return

        self.last_feedback_index = index
        previous_name = START[0] if index == 0 else ROOM_WAYPOINTS[index - 1][0]
        waypoint_name, x, y, _ = ROOM_WAYPOINTS[index]
        self.node.get_logger().info(
            f"正在导航：从{previous_name}出发，前往第{index + 1}个航点"
            f"{waypoint_name} (x={x:.2f}, y={y:.2f})。"
            "前一航点是否成功以最终 missed_waypoints 结果为准。"
        )

    def _report_route_result(self, status, missed_waypoints):
        missed = set(missed_waypoints)
        for index, (destination, x, y, _yaw) in enumerate(ROOM_WAYPOINTS):
            origin = START[0] if index == 0 else ROOM_WAYPOINTS[index - 1][0]
            if index in missed:
                self.node.get_logger().error(
                    f"航点失败：从{origin}前往{destination}"
                    f"(x={x:.2f}, y={y:.2f})，Waypoint Follower报告该点遗漏。"
                )
            elif status == GoalStatus.STATUS_SUCCEEDED:
                self.node.get_logger().info(
                    f"抵达{destination}成功：{origin} -> {destination}"
                )
            else:
                self.node.get_logger().warning(
                    f"航点结果未确认：{origin} -> {destination}；"
                    "多航点Action未以SUCCEEDED结束。"
                )

        if status == GoalStatus.STATUS_SUCCEEDED and not missed:
            self.node.get_logger().info(
                "已抵达终点起点，主卧 -> 小孩房 -> 起点全部成功；"
                "多航点导航全过程完成。"
            )
        elif status == GoalStatus.STATUS_CANCELED:
            self.node.get_logger().error("多航点导航已取消，后续航点未保证执行。")
        else:
            self.node.get_logger().error(
                f"多航点导航失败，Action状态码为{status}。"
            )

    def _wait_for_environment(self):
        deadline = time.monotonic() + READY_TIMEOUT_SEC
        required_names = set(REQUIRED_NODES)
        action_ready = False
        node_names = set()
        while time.monotonic() < deadline:
            node_names = set(self.node.get_node_names())
            action_ready = self.client.wait_for_server(timeout_sec=0.1)
            if required_names.issubset(node_names) and self.clock_seen and action_ready:
                return
            rclpy.spin_once(self.node, timeout_sec=0.1)

        missing = [
            label for name, label in REQUIRED_NODES.items()
            if name not in node_names
        ]
        if not action_ready:
            missing.append("/follow_waypoints Action Server")
        if not self.clock_seen:
            missing.append("Gazebo仿真时钟 /clock")
        details = "、".join(missing) if missing else "Nav2尚未就绪"
        self.fail(
            "未检测到完整的AU9仿真主环境；缺少："
            f"{details}。请先在另一个终端运行 "
            "`./scripts/start_au9_manual_nav2.sh`，等待Gazebo、RViz2、"
            "AMCL和Nav2启动完成后，再运行本多航点测试。"
        )

    def test_follow_waypoints_visits_two_rooms_then_returns_home(self):
        self._wait_for_environment()

        goal = FollowWaypoints.Goal()
        goal.poses = [
            self._pose(x, y, yaw) for _, x, y, yaw in ROOM_WAYPOINTS
        ]
        send_future = self.client.send_goal_async(
            goal,
            feedback_callback=self._on_waypoint_feedback,
        )
        if not self._spin_until(lambda: send_future.done(), timeout=15.0):
            self.node.get_logger().error("发送FollowWaypoints目标超时。")
            self.fail("FollowWaypoints request timed out")
        handle = send_future.result()
        if not handle.accepted:
            self.node.get_logger().error("Waypoint Follower拒绝了多航点目标。")
            self.fail("multi-room goal was rejected")
        self.node.get_logger().info("多航点任务已接受：起点 -> 主卧 -> 小孩房 -> 起点。")

        result_future = handle.get_result_async()
        finished = self._spin_until(lambda: result_future.done(), timeout=360.0)
        if not finished:
            self.node.get_logger().error(
                f"多航点导航超时，当前航点反馈索引：{self.last_feedback_index}；"
                "正在请求取消任务。"
            )
            cancel_future = handle.cancel_goal_async()
            self._spin_until(lambda: cancel_future.done(), timeout=10.0)
            self._spin_until(lambda: result_future.done(), timeout=20.0)
        self.assertTrue(finished, "multi-room FollowWaypoints route timed out")

        wrapped_result = result_future.result()
        missed_waypoints = list(wrapped_result.result.missed_waypoints)
        self._report_route_result(wrapped_result.status, missed_waypoints)
        self.assertEqual(
            wrapped_result.status,
            GoalStatus.STATUS_SUCCEEDED,
            "FollowWaypoints did not succeed",
        )
        self.assertEqual(
            missed_waypoints,
            [],
            "one or more room/home waypoints were missed",
        )
        self.assertTrue(
            {0, 1, 2}.issubset(set(self.feedback_indices)),
            f"did not observe all waypoint feedback: {self.feedback_indices}",
        )
