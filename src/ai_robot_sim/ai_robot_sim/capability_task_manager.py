from collections import OrderedDict
from dataclasses import dataclass
import math
import time
from threading import Lock

import rclpy
from action_msgs.msg import GoalStatus
from ai_robot_interfaces.action import ExecuteCapabilityTask
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.task import Future
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import Bool, String


@dataclass(frozen=True)
class CachedResult:
    outcome: int
    detail: str
    elapsed_sec: float
    minimum_scan_range: float
    image_width: int
    image_height: int


class CapabilityTaskManager(Node):
    def __init__(self) -> None:
        super().__init__("capability_task_manager")
        self.declare_parameter("minimum_x", -3.5)
        self.declare_parameter("maximum_x", 3.5)
        self.declare_parameter("minimum_y", -2.5)
        self.declare_parameter("maximum_y", 2.5)
        self.declare_parameter("sensor_timeout", 1.0)
        self.declare_parameter("nav_server_timeout", 12.0)
        self.declare_parameter("maximum_cached_tasks", 32)
        self._minimum_x = float(self.get_parameter("minimum_x").value)
        self._maximum_x = float(self.get_parameter("maximum_x").value)
        self._minimum_y = float(self.get_parameter("minimum_y").value)
        self._maximum_y = float(self.get_parameter("maximum_y").value)
        self._sensor_timeout = float(self.get_parameter("sensor_timeout").value)
        self._nav_server_timeout = float(
            self.get_parameter("nav_server_timeout").value
        )
        self._maximum_cached_tasks = int(
            self.get_parameter("maximum_cached_tasks").value
        )

        self._callback_group = ReentrantCallbackGroup()
        self._active_lock = Lock()
        self._sleep_lock = Lock()
        self._active = False
        self._safety_stop = False
        self._latest_scan = None
        self._latest_scan_time = 0.0
        self._latest_image = None
        self._latest_image_time = 0.0
        self._cache = OrderedDict()
        self._sleep_waiters = []

        self._status_publisher = self.create_publisher(
            String, "/capability_task/status", 10
        )
        self.create_subscription(
            LaserScan,
            "/scan",
            self._on_scan,
            10,
            callback_group=self._callback_group,
        )
        self.create_subscription(
            Image,
            "/camera/image_raw",
            self._on_image,
            10,
            callback_group=self._callback_group,
        )
        self.create_subscription(
            Bool,
            "/safety_stop",
            self._on_safety_stop,
            10,
            callback_group=self._callback_group,
        )
        self._nav_client = ActionClient(
            self,
            NavigateToPose,
            "/navigate_to_pose",
            callback_group=self._callback_group,
        )
        self._action_server = ActionServer(
            self,
            ExecuteCapabilityTask,
            "/execute_capability_task",
            execute_callback=self._execute,
            goal_callback=self._on_goal,
            cancel_callback=self._on_cancel,
            callback_group=self._callback_group,
        )
        self.create_timer(
            0.02,
            self._wake_sleepers,
            callback_group=self._callback_group,
        )

    def _on_scan(self, scan: LaserScan) -> None:
        self._latest_scan = scan
        self._latest_scan_time = time.monotonic()

    def _on_image(self, image: Image) -> None:
        self._latest_image = image
        self._latest_image_time = time.monotonic()

    def _on_safety_stop(self, safety_stop: Bool) -> None:
        self._safety_stop = safety_stop.data

    def _on_goal(self, _goal_request) -> GoalResponse:
        with self._active_lock:
            if self._active:
                return GoalResponse.REJECT
            self._active = True
        return GoalResponse.ACCEPT

    def _on_cancel(self, _goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def _validate(self, request):
        if not request.task_id:
            return ExecuteCapabilityTask.Result.INVALID_TASK, "task_id_required"
        if request.capability != "navigate_and_observe":
            return ExecuteCapabilityTask.Result.INVALID_TASK, "unsupported_capability"
        if request.target_pose.header.frame_id != "map":
            return ExecuteCapabilityTask.Result.INVALID_TASK, "target_frame_must_be_map"
        position = request.target_pose.pose.position
        if not math.isfinite(position.x) or not math.isfinite(position.y):
            return ExecuteCapabilityTask.Result.INVALID_TASK, "target_not_finite"
        if (
            position.x < self._minimum_x
            or position.x > self._maximum_x
            or position.y < self._minimum_y
            or position.y > self._maximum_y
        ):
            return ExecuteCapabilityTask.Result.OUT_OF_BOUNDS, "target_out_of_bounds"
        if request.timeout_sec <= 0.0:
            return ExecuteCapabilityTask.Result.INVALID_TASK, "timeout_must_be_positive"
        return None

    def _sensor_is_fresh(self, timestamp: float) -> bool:
        return time.monotonic() - timestamp <= self._sensor_timeout

    def _required_sensors_available(self, request) -> bool:
        scan_ok = not request.require_scan or (
            self._latest_scan is not None
            and self._sensor_is_fresh(self._latest_scan_time)
        )
        image_ok = not request.require_image or (
            self._latest_image is not None
            and self._sensor_is_fresh(self._latest_image_time)
        )
        return scan_ok and image_ok

    def _publish_feedback(self, goal_handle, phase: int, status: str, start: float):
        feedback = ExecuteCapabilityTask.Feedback()
        feedback.phase = phase
        feedback.status = status
        feedback.elapsed_sec = float(time.monotonic() - start)
        goal_handle.publish_feedback(feedback)
        message = String()
        message.data = status
        self._status_publisher.publish(message)

    def _make_result(
        self,
        request,
        outcome: int,
        detail: str,
        start: float,
        replayed: bool = False,
    ):
        result = ExecuteCapabilityTask.Result()
        result.outcome = outcome
        result.task_id = request.task_id
        result.detail = detail
        result.replayed = replayed
        result.elapsed_sec = float(time.monotonic() - start)
        finite_ranges = []
        if self._latest_scan is not None:
            finite_ranges = [
                value
                for value in self._latest_scan.ranges
                if math.isfinite(value)
            ]
        result.minimum_scan_range = (
            float(min(finite_ranges)) if finite_ranges else float("nan")
        )
        if self._latest_image is not None:
            result.image_width = self._latest_image.width
            result.image_height = self._latest_image.height
        return result

    def _cache_result(self, result) -> None:
        self._cache[result.task_id] = CachedResult(
            outcome=result.outcome,
            detail=result.detail,
            elapsed_sec=result.elapsed_sec,
            minimum_scan_range=result.minimum_scan_range,
            image_width=result.image_width,
            image_height=result.image_height,
        )
        self._cache.move_to_end(result.task_id)
        while len(self._cache) > self._maximum_cached_tasks:
            self._cache.popitem(last=False)

    def _replay_result(self, request, cached: CachedResult):
        result = ExecuteCapabilityTask.Result()
        result.outcome = cached.outcome
        result.task_id = request.task_id
        result.detail = cached.detail
        result.replayed = True
        result.elapsed_sec = cached.elapsed_sec
        result.minimum_scan_range = cached.minimum_scan_range
        result.image_width = cached.image_width
        result.image_height = cached.image_height
        return result

    async def _sleep(self, duration: float) -> None:
        future = Future()
        with self._sleep_lock:
            self._sleep_waiters.append(
                (time.monotonic() + duration, future)
            )
        await future

    def _wake_sleepers(self) -> None:
        now = time.monotonic()
        ready = []
        with self._sleep_lock:
            pending = []
            for deadline, future in self._sleep_waiters:
                if deadline <= now:
                    ready.append(future)
                else:
                    pending.append((deadline, future))
            self._sleep_waiters = pending
        for future in ready:
            if not future.done():
                future.set_result(None)

    async def _cancel_navigation(self, navigation_goal) -> None:
        if navigation_goal is not None:
            cancel_future = navigation_goal.cancel_goal_async()
            await cancel_future

    async def _execute(self, goal_handle):
        request = goal_handle.request
        start = time.monotonic()
        navigation_goal = None
        try:
            self._publish_feedback(
                goal_handle,
                ExecuteCapabilityTask.Feedback.VALIDATING,
                "validating",
                start,
            )
            cached = self._cache.get(request.task_id)
            if cached is not None:
                goal_handle.succeed()
                return self._replay_result(request, cached)

            validation_error = self._validate(request)
            if validation_error is not None:
                outcome, detail = validation_error
                result = self._make_result(request, outcome, detail, start)
                goal_handle.abort()
                self._cache_result(result)
                return result
            if not self._required_sensors_available(request):
                result = self._make_result(
                    request,
                    ExecuteCapabilityTask.Result.SENSOR_UNAVAILABLE,
                    "required_sensor_unavailable",
                    start,
                )
                goal_handle.abort()
                self._cache_result(result)
                return result

            self._publish_feedback(
                goal_handle,
                ExecuteCapabilityTask.Feedback.NAVIGATING,
                "waiting_for_nav2",
                start,
            )
            nav_deadline = time.monotonic() + min(
                request.timeout_sec, self._nav_server_timeout
            )
            while not self._nav_client.server_is_ready():
                if time.monotonic() >= nav_deadline:
                    result = self._make_result(
                        request,
                        ExecuteCapabilityTask.Result.TIMED_OUT,
                        "nav2_server_timeout",
                        start,
                    )
                    goal_handle.abort()
                    self._cache_result(result)
                    return result
                await self._sleep(0.05)

            nav_goal = NavigateToPose.Goal()
            nav_goal.pose = request.target_pose
            nav_goal.pose.header.stamp = self.get_clock().now().to_msg()
            send_future = self._nav_client.send_goal_async(nav_goal)
            navigation_goal = await send_future
            if not navigation_goal.accepted:
                result = self._make_result(
                    request,
                    ExecuteCapabilityTask.Result.NAVIGATION_FAILED,
                    "navigation_goal_rejected",
                    start,
                )
                goal_handle.abort()
                self._cache_result(result)
                return result

            result_future = navigation_goal.get_result_async()
            while not result_future.done():
                elapsed = time.monotonic() - start
                if goal_handle.is_cancel_requested:
                    await self._cancel_navigation(navigation_goal)
                    result = self._make_result(
                        request,
                        ExecuteCapabilityTask.Result.CANCELED,
                        "task_canceled",
                        start,
                    )
                    goal_handle.canceled()
                    self._cache_result(result)
                    return result
                if self._safety_stop or (
                    request.require_scan
                    and not self._sensor_is_fresh(self._latest_scan_time)
                ):
                    await self._cancel_navigation(navigation_goal)
                    result = self._make_result(
                        request,
                        ExecuteCapabilityTask.Result.SAFETY_TRIGGERED,
                        "safety_stop_active",
                        start,
                    )
                    goal_handle.abort()
                    self._cache_result(result)
                    return result
                if elapsed >= request.timeout_sec:
                    await self._cancel_navigation(navigation_goal)
                    result = self._make_result(
                        request,
                        ExecuteCapabilityTask.Result.TIMED_OUT,
                        "task_timeout",
                        start,
                    )
                    goal_handle.abort()
                    self._cache_result(result)
                    return result
                self._publish_feedback(
                    goal_handle,
                    ExecuteCapabilityTask.Feedback.NAVIGATING,
                    "navigating",
                    start,
                )
                await self._sleep(0.05)

            navigation_result = result_future.result()
            if navigation_result.status != GoalStatus.STATUS_SUCCEEDED:
                result = self._make_result(
                    request,
                    ExecuteCapabilityTask.Result.NAVIGATION_FAILED,
                    "navigation_failed",
                    start,
                )
                goal_handle.abort()
                self._cache_result(result)
                return result

            self._publish_feedback(
                goal_handle,
                ExecuteCapabilityTask.Feedback.PERCEIVING,
                "perceiving",
                start,
            )
            if not self._required_sensors_available(request):
                result = self._make_result(
                    request,
                    ExecuteCapabilityTask.Result.SENSOR_UNAVAILABLE,
                    "sensor_stale_at_goal",
                    start,
                )
                goal_handle.abort()
                self._cache_result(result)
                return result

            result = self._make_result(
                request,
                ExecuteCapabilityTask.Result.SUCCEEDED,
                "navigation_and_perception_succeeded",
                start,
            )
            goal_handle.succeed()
            self._cache_result(result)
            return result
        except Exception as error:
            self.get_logger().error(f"Task execution failed: {error!r}")
            result = self._make_result(
                request,
                ExecuteCapabilityTask.Result.NAVIGATION_FAILED,
                "task_manager_exception",
                start,
            )
            goal_handle.abort()
            self._cache_result(result)
            return result
        finally:
            with self._active_lock:
                self._active = False


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CapabilityTaskManager()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    except RuntimeError as error:
        node.get_logger().error(f"Executor stopped unexpectedly: {error!r}")
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
