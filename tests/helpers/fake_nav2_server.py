#!/usr/bin/env python3

from threading import Lock
import time

import rclpy
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.task import Future
from std_msgs.msg import Int32, String


class FakeNav2Server(Node):
    def __init__(self) -> None:
        super().__init__("fake_nav2_server")
        self._mode = "success"
        self._goal_count = 0
        self._callback_group = ReentrantCallbackGroup()
        self._sleep_lock = Lock()
        self._sleep_waiters = []
        self._count_publisher = self.create_publisher(
            Int32, "/test/nav_goal_count", 10
        )
        self.create_subscription(
            String,
            "/test/nav_mode",
            self._on_mode,
            10,
            callback_group=self._callback_group,
        )
        self._server = ActionServer(
            self,
            NavigateToPose,
            "/navigate_to_pose",
            execute_callback=self._execute,
            callback_group=self._callback_group,
        )
        self.create_timer(
            0.02,
            self._wake_sleepers,
            callback_group=self._callback_group,
        )

    def _on_mode(self, message: String) -> None:
        self._mode = message.data

    async def _sleep(self, duration):
        future = Future()
        with self._sleep_lock:
            self._sleep_waiters.append(
                (time.monotonic() + duration, future)
            )
        await future

    def _wake_sleepers(self):
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

    async def _execute(self, goal_handle):
        self._goal_count += 1
        count = Int32()
        count.data = self._goal_count
        self._count_publisher.publish(count)
        mode = self._mode
        if mode == "hang":
            while not goal_handle.is_cancel_requested:
                await self._sleep(0.02)
            goal_handle.canceled()
            return NavigateToPose.Result()
        await self._sleep(0.08)
        if goal_handle.is_cancel_requested:
            goal_handle.canceled()
        elif mode == "fail":
            goal_handle.abort()
        else:
            goal_handle.succeed()
        return NavigateToPose.Result()


def main() -> None:
    rclpy.init()
    node = FakeNav2Server()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, RuntimeError):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
