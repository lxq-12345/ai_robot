import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class ManualMotionDemo(Node):
    def __init__(self) -> None:
        super().__init__("manual_motion_demo")
        self.declare_parameter("linear_speed", 0.20)
        self.declare_parameter("angular_speed", 0.60)
        self.declare_parameter("step_duration", 2.0)
        self._publisher = self.create_publisher(Twist, "/cmd_vel_raw", 10)

    def _publish_for(self, label: str, linear_x: float = 0.0, angular_z: float = 0.0) -> None:
        duration = float(self.get_parameter("step_duration").value)
        command = Twist()
        command.linear.x = linear_x
        command.angular.z = angular_z
        self.get_logger().info(label)
        deadline = time.monotonic() + duration
        while rclpy.ok() and time.monotonic() < deadline:
            self._publisher.publish(command)
            rclpy.spin_once(self, timeout_sec=0.05)

    def run_demo(self) -> None:
        linear = float(self.get_parameter("linear_speed").value)
        angular = float(self.get_parameter("angular_speed").value)
        time.sleep(1.0)
        self._publish_for("forward", linear_x=linear)
        self._publish_for("stop")
        self._publish_for("backward", linear_x=-linear)
        self._publish_for("stop")
        self._publish_for("turn_left", angular_z=angular)
        self._publish_for("stop")
        self._publish_for("turn_right", angular_z=-angular)
        self._publish_for("stop")
        self.get_logger().info("manual motion demo finished")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ManualMotionDemo()
    try:
        node.run_demo()
    except KeyboardInterrupt:
        pass
    finally:
        node._publish_for("final_stop", linear_x=0.0, angular_z=0.0)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
