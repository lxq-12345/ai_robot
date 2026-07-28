import math

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class ScanObstacleMonitor(Node):
    def __init__(self) -> None:
        super().__init__("scan_obstacle_monitor")
        self.declare_parameter("warning_distance", 0.50)
        self._warning_distance = float(self.get_parameter("warning_distance").value)
        self._publisher = self.create_publisher(DiagnosticArray, "/diagnostics", 10)
        self.create_subscription(LaserScan, "/scan", self._on_scan, 10)

    def _on_scan(self, scan: LaserScan) -> None:
        finite_ranges = [value for value in scan.ranges if math.isfinite(value)]
        nearest = min(finite_ranges) if finite_ranges else float("inf")
        status = DiagnosticStatus()
        status.name = "s1_m4.scan_obstacle_chain"
        status.hardware_id = "gazebo_laser"
        status.level = DiagnosticStatus.WARN if nearest < self._warning_distance else DiagnosticStatus.OK
        status.message = "obstacle_near" if status.level == DiagnosticStatus.WARN else "obstacle_clear"
        status.values = [
            KeyValue(key="frame_id", value=scan.header.frame_id),
            KeyValue(key="nearest_range_m", value=f"{nearest:.3f}"),
            KeyValue(key="sample_count", value=str(len(scan.ranges))),
        ]
        array = DiagnosticArray()
        array.header.stamp = self.get_clock().now().to_msg()
        array.status.append(status)
        self._publisher.publish(array)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ScanObstacleMonitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, RuntimeError):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
