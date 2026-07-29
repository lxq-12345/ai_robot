import argparse
import threading
import time
from dataclasses import dataclass
from typing import Callable

import rclpy
from action_msgs.msg import GoalStatus
from ai_robot_interfaces.action import ExecuteCapabilityTask
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Bool


STATUS_NAMES = {
    GoalStatus.STATUS_UNKNOWN: "UNKNOWN",
    GoalStatus.STATUS_ACCEPTED: "ACCEPTED",
    GoalStatus.STATUS_EXECUTING: "EXECUTING",
    GoalStatus.STATUS_CANCELING: "CANCELING",
    GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED",
    GoalStatus.STATUS_CANCELED: "CANCELED",
    GoalStatus.STATUS_ABORTED: "ABORTED",
}

M6_OUTCOME_NAMES = {
    ExecuteCapabilityTask.Result.SUCCEEDED: "SUCCEEDED",
    ExecuteCapabilityTask.Result.INVALID_TASK: "INVALID_TASK",
    ExecuteCapabilityTask.Result.OUT_OF_BOUNDS: "OUT_OF_BOUNDS",
    ExecuteCapabilityTask.Result.NAVIGATION_FAILED: "NAVIGATION_FAILED",
    ExecuteCapabilityTask.Result.TIMED_OUT: "TIMED_OUT",
    ExecuteCapabilityTask.Result.CANCELED: "CANCELED",
    ExecuteCapabilityTask.Result.SENSOR_UNAVAILABLE: "SENSOR_UNAVAILABLE",
    ExecuteCapabilityTask.Result.SAFETY_TRIGGERED: "SAFETY_TRIGGERED",
}

M6_PHASE_NAMES = {
    ExecuteCapabilityTask.Feedback.VALIDATING: "VALIDATING",
    ExecuteCapabilityTask.Feedback.NAVIGATING: "NAVIGATING",
    ExecuteCapabilityTask.Feedback.PERCEIVING: "PERCEIVING",
}


@dataclass
class Observation:
    odom_received: bool = False
    maximum_linear_speed: float = 0.0
    maximum_angular_speed: float = 0.0
    last_motion_time: float = 0.0


def make_nav_goal(x: float, y: float) -> NavigateToPose.Goal:
    goal = NavigateToPose.Goal()
    goal.pose.header.frame_id = "map"
    goal.pose.pose.position.x = x
    goal.pose.pose.position.y = y
    goal.pose.pose.orientation.w = 1.0
    return goal


def make_capability_goal(
    task_id: str,
    x: float,
    y: float,
) -> ExecuteCapabilityTask.Goal:
    goal = ExecuteCapabilityTask.Goal()
    goal.task_id = task_id
    goal.capability = "navigate_and_observe"
    goal.target_pose.header.frame_id = "map"
    goal.target_pose.pose.position.x = x
    goal.target_pose.pose.position.y = y
    goal.target_pose.pose.orientation.w = 1.0
    goal.timeout_sec = 60.0
    goal.require_scan = True
    goal.require_image = True
    return goal


class ManualExperience(Node):
    def __init__(self) -> None:
        super().__init__("manual_m5_m6_experience")
        self.nav_client = ActionClient(
            self,
            NavigateToPose,
            "/navigate_to_pose",
        )
        self.task_client = ActionClient(
            self,
            ExecuteCapabilityTask,
            "/execute_capability_task",
        )
        self.initial_pose = self.create_publisher(
            PoseWithCovarianceStamped,
            "/initialpose",
            10,
        )
        self.safety_stop = self.create_publisher(Bool, "/safety_stop", 10)
        self.observation = Observation()
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)
        self.create_subscription(Twist, "/cmd_vel", self._on_velocity, 10)
        self._last_feedback_print = 0.0
        self._last_task_feedback_print = 0.0
        self._last_task_phase = 0

    def _on_odom(self, _message: Odometry) -> None:
        self.observation.odom_received = True

    def _on_velocity(self, message: Twist) -> None:
        linear = abs(message.linear.x)
        angular = abs(message.angular.z)
        self.observation.maximum_linear_speed = max(
            self.observation.maximum_linear_speed,
            linear,
        )
        self.observation.maximum_angular_speed = max(
            self.observation.maximum_angular_speed,
            angular,
        )
        if linear > 0.01 or angular > 0.01:
            self.observation.last_motion_time = time.monotonic()

    @staticmethod
    def _wait_future(future, timeout: float):
        deadline = time.monotonic() + timeout
        while not future.done() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not future.done():
            raise TimeoutError("ROS action response timed out")
        return future.result()

    @staticmethod
    def _wait_for(predicate: Callable[[], bool], timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.10)
        return False

    def wait_until_ready(self) -> None:
        print("Waiting for Gazebo odometry and action servers...")
        if not self._wait_for(
            lambda: self.observation.odom_received,
            timeout=40.0,
        ):
            raise RuntimeError("Gazebo odometry is unavailable")
        if not self.nav_client.wait_for_server(timeout_sec=45.0):
            raise RuntimeError("Nav2 NavigateToPose server is unavailable")
        if not self.task_client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError("M6 capability task server is unavailable")
        print("System ready.")

    def set_initial_pose(self) -> None:
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = 0.25
        pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.068
        for _ in range(6):
            pose.header.stamp = self.get_clock().now().to_msg()
            self.initial_pose.publish(pose)
            time.sleep(0.10)
        print("Initial pose published at map (0.0, 0.0).")
        time.sleep(2.0)

    def _on_nav_feedback(self, message) -> None:
        now = time.monotonic()
        if now - self._last_feedback_print < 1.0:
            return
        self._last_feedback_print = now
        feedback = message.feedback
        print(
            "  M5 NAVIGATING:"
            f" remaining={feedback.distance_remaining:.2f} m,"
            f" recoveries={feedback.number_of_recoveries}"
        )

    def send_m5_goal(
        self,
        x: float,
        y: float,
        cancel_on_enter: bool = False,
    ) -> bool:
        print(f"M5 goal: map ({x:.2f}, {y:.2f})")
        request = self.nav_client.send_goal_async(
            make_nav_goal(x, y),
            feedback_callback=self._on_nav_feedback,
        )
        handle = self._wait_future(request, timeout=10.0)
        if not handle.accepted:
            print("  M5 goal rejected.")
            return False
        if cancel_on_enter:
            input("  Observe motion in Gazebo, then press Enter to cancel: ")
            cancel = self._wait_future(
                handle.cancel_goal_async(),
                timeout=10.0,
            )
            if not cancel.goals_canceling:
                print("  M5 cancellation was rejected.")
                return False
        response = self._wait_future(
            handle.get_result_async(),
            timeout=90.0,
        )
        status = STATUS_NAMES.get(response.status, str(response.status))
        print(f"  M5 result: {status}")
        expected = (
            GoalStatus.STATUS_CANCELED
            if cancel_on_enter
            else GoalStatus.STATUS_SUCCEEDED
        )
        return response.status == expected

    def _on_task_feedback(self, message) -> None:
        feedback = message.feedback
        now = time.monotonic()
        phase_changed = feedback.phase != self._last_task_phase
        if (
            not phase_changed
            and now - self._last_task_feedback_print < 1.0
        ):
            return
        self._last_task_feedback_print = now
        self._last_task_phase = feedback.phase
        phase = M6_PHASE_NAMES.get(feedback.phase, str(feedback.phase))
        print(
            f"  M6 {phase}: {feedback.status}"
            f" ({feedback.elapsed_sec:.1f} s)"
        )

    def _publish_safety(self, active: bool) -> None:
        message = Bool(data=active)
        for _ in range(3):
            self.safety_stop.publish(message)
            time.sleep(0.05)

    def send_m6_goal(
        self,
        task_id: str,
        x: float,
        y: float,
        safety_on_enter: bool = False,
    ):
        print(f"M6 task {task_id}: map ({x:.2f}, {y:.2f})")
        self._last_task_feedback_print = 0.0
        self._last_task_phase = 0
        request = self.task_client.send_goal_async(
            make_capability_goal(task_id, x, y),
            feedback_callback=self._on_task_feedback,
        )
        handle = self._wait_future(request, timeout=10.0)
        if not handle.accepted:
            print("  M6 task rejected.")
            return None
        if safety_on_enter:
            input(
                "  Observe motion in Gazebo, then press Enter"
                " to trigger safety stop: "
            )
            self._publish_safety(True)
        try:
            response = self._wait_future(
                handle.get_result_async(),
                timeout=75.0,
            )
        finally:
            if safety_on_enter:
                self._publish_safety(False)
        result = response.result
        status = STATUS_NAMES.get(response.status, str(response.status))
        outcome = M6_OUTCOME_NAMES.get(result.outcome, str(result.outcome))
        print(
            f"  M6 result: status={status}, outcome={outcome},"
            f" replayed={result.replayed}, detail={result.detail}"
        )
        print(
            f"  Perception: min_scan={result.minimum_scan_range:.2f} m,"
            f" image={result.image_width}x{result.image_height},"
            f" elapsed={result.elapsed_sec:.2f} s"
        )
        return response

    def stopped_after(self, since: float, timeout: float = 2.0) -> bool:
        time.sleep(timeout)
        return self.observation.last_motion_time <= since + 0.5


def prompt_step(message: str) -> None:
    input(f"\n{message}\nPress Enter to continue: ")


def run_m5(node: ManualExperience) -> list[tuple[str, bool]]:
    results = []
    prompt_step(
        "M5-1: Start a longer navigation and cancel it manually."
    )
    canceled = node.send_m5_goal(2.0, -1.0, cancel_on_enter=True)
    cancel_time = time.monotonic()
    results.append(("M5 manual cancellation", canceled))
    results.append(
        ("M5 stopped after cancellation", node.stopped_after(cancel_time))
    )
    prompt_step(
        "M5-2: Observe direct Nav2 navigation to a reachable target."
    )
    results.append(
        ("M5 reachable navigation", node.send_m5_goal(-0.5, -0.3))
    )
    return results


def run_m6(node: ManualExperience) -> list[tuple[str, bool]]:
    results = []
    task_id = f"manual-m6-{int(time.time())}"
    prompt_step(
        "M6-1: Observe VALIDATING, NAVIGATING and PERCEIVING feedback."
    )
    response = node.send_m6_goal(task_id, -0.5, 0.3)
    succeeded = (
        response is not None
        and response.status == GoalStatus.STATUS_SUCCEEDED
        and response.result.outcome
        == ExecuteCapabilityTask.Result.SUCCEEDED
        and response.result.minimum_scan_range > 0.0
        and response.result.image_width > 0
        and response.result.image_height > 0
    )
    results.append(("M6 navigate and observe", succeeded))

    prompt_step(
        "M6-2: Replay the same task ID; the robot must not move again."
    )
    replay_start = time.monotonic()
    replay = node.send_m6_goal(task_id, -0.5, 0.3)
    replayed = (
        replay is not None
        and replay.status == GoalStatus.STATUS_SUCCEEDED
        and replay.result.replayed
    )
    results.append(("M6 idempotent replay", replayed))
    results.append(
        ("M6 no motion during replay", node.stopped_after(replay_start))
    )

    prompt_step(
        "M6-3: Start a task and trigger the simulated safety stop."
    )
    safety = node.send_m6_goal(
        f"{task_id}-safety",
        2.0,
        -1.0,
        safety_on_enter=True,
    )
    safety_time = time.monotonic()
    safety_triggered = (
        safety is not None
        and safety.result.outcome
        == ExecuteCapabilityTask.Result.SAFETY_TRIGGERED
    )
    results.append(("M6 safety-trigger result", safety_triggered))
    results.append(
        ("M6 stopped after safety trigger", node.stopped_after(safety_time))
    )
    return results


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Guided S1-1-M5 and S1-1-M6 Gazebo experience test."
    )
    parser.add_argument(
        "--scenario",
        choices=("all", "m5", "m6"),
        default="all",
    )
    return parser.parse_known_args(args)[0]


def main(args=None) -> None:
    options = parse_args(args)
    rclpy.init(args=args)
    node = ManualExperience()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    results: list[tuple[str, bool]] = []
    exit_code = 0
    try:
        print("S1-1-M5/M6 guided manual experience test (Gazebo only)")
        print("No direct /cmd_vel or /cmd_vel_raw publication is used.")
        node.wait_until_ready()
        node.set_initial_pose()
        if options.scenario in ("all", "m5"):
            results.extend(run_m5(node))
        if options.scenario in ("all", "m6"):
            results.extend(run_m6(node))
    except (KeyboardInterrupt, EOFError):
        print("\nManual experience interrupted.")
        exit_code = 130
    except (RuntimeError, TimeoutError) as error:
        print(f"\nManual experience failed: {error}")
        exit_code = 1
    finally:
        print("\nAcceptance summary")
        for name, passed in results:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        if any(not passed for _, passed in results):
            exit_code = 1
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        spin_thread.join(timeout=2.0)
    raise SystemExit(exit_code)
