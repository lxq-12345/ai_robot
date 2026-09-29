import time
from dataclasses import dataclass

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


@dataclass(frozen=True)
class VelocityLimit:
    linear: float = 0.35
    angular: float = 1.20


def clamp_twist(command: Twist, limit: VelocityLimit) -> Twist:
    bounded = Twist()
    bounded.linear.x = max(-limit.linear, min(limit.linear, command.linear.x))
    bounded.angular.z = max(-limit.angular, min(limit.angular, command.angular.z))
    return bounded


class CmdVelGuard(Node):
    def __init__(self) -> None:
        super().__init__("cmd_vel_guard")
        self.declare_parameter("max_linear_speed", 0.35)
        self.declare_parameter("max_angular_speed", 1.20)
        self.declare_parameter("command_timeout", 0.50)
        self.declare_parameter("require_scan", False)
        self.declare_parameter("scan_timeout", 0.75)
        self.declare_parameter("input_topic", "/cmd_vel_raw")
        self.declare_parameter("output_topic", "/cmd_vel")
        self._limit = VelocityLimit(
            linear=float(self.get_parameter("max_linear_speed").value),
            angular=float(self.get_parameter("max_angular_speed").value),
        )
        self._timeout = float(self.get_parameter("command_timeout").value)
        self._require_scan = bool(self.get_parameter("require_scan").value)
        self._scan_timeout = float(self.get_parameter("scan_timeout").value)
        input_topic = str(self.get_parameter("input_topic").value)
        output_topic = str(self.get_parameter("output_topic").value)
        self._last_command_time = time.monotonic()
        self._last_scan_time = time.monotonic()
        self._publisher = self.create_publisher(Twist, output_topic, 10)
        self.create_subscription(Twist, input_topic, self._on_command, 10)
        self.create_subscription(LaserScan, "/scan", self._on_scan, 10)
        self.create_timer(0.05, self._enforce_timeout)

    def _on_command(self, command: Twist) -> None:
        self._last_command_time = time.monotonic()
        if not self._scan_is_fresh():
            self._publisher.publish(Twist())
            return
        self._publisher.publish(clamp_twist(command, self._limit))

    def _on_scan(self, _scan: LaserScan) -> None:
        self._last_scan_time = time.monotonic()

    def _scan_is_fresh(self) -> bool:
        scan_age = time.monotonic() - self._last_scan_time
        return not self._require_scan or scan_age < self._scan_timeout

    def _enforce_timeout(self) -> None:
        command_expired = (
            time.monotonic() - self._last_command_time >= self._timeout
        )
        if command_expired or not self._scan_is_fresh():
            self._publisher.publish(Twist())


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CmdVelGuard()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
