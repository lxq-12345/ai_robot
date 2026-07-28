import rclpy
from rclpy.node import Node


def status_line(state: str) -> str:
    return f"ai_robot_py_example:{state}"


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Node("baseline_py_node")
    try:
        node.get_logger().info(status_line("ready"))
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
