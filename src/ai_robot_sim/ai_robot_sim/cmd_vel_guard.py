from dataclasses import dataclass

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


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
        self._limit = VelocityLimit(
            linear=float(self.get_parameter("max_linear_speed").value),
            angular=float(self.get_parameter("max_angular_speed").value),
        )
        self._timeout = float(self.get_parameter("command_timeout").value)
        self._last_command_time = self.get_clock().now()
        self._publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(Twist, "/cmd_vel_raw", self._on_command, 10)
        self.create_timer(0.05, self._enforce_timeout)

    def _on_command(self, command: Twist) -> None:
        self._last_command_time = self.get_clock().now()
        self._publisher.publish(clamp_twist(command, self._limit))

    def _enforce_timeout(self) -> None:
        elapsed = (self.get_clock().now() - self._last_command_time).nanoseconds / 1e9
        if elapsed >= self._timeout:
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
