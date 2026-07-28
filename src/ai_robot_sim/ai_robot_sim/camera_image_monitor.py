import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image


class CameraImageMonitor(Node):
    def __init__(self) -> None:
        super().__init__("camera_image_monitor")
        self._latest_info = None
        self._publisher = self.create_publisher(DiagnosticArray, "/diagnostics", 10)
        self.create_subscription(CameraInfo, "/camera/camera_info", self._on_camera_info, 10)
        self.create_subscription(Image, "/camera/image_raw", self._on_image, 10)

    def _on_camera_info(self, camera_info: CameraInfo) -> None:
        self._latest_info = camera_info

    def _on_image(self, image: Image) -> None:
        expected_bytes = image.width * image.height
        has_data = len(image.data) >= expected_bytes
        info_matches = (
            self._latest_info is not None
            and self._latest_info.width == image.width
            and self._latest_info.height == image.height
            and self._latest_info.header.frame_id == image.header.frame_id
        )

        status = DiagnosticStatus()
        status.name = "s1_m4.camera_image_chain"
        status.hardware_id = "gazebo_camera"
        status.level = DiagnosticStatus.OK if has_data and info_matches else DiagnosticStatus.WARN
        status.message = "image_info_consistent" if status.level == DiagnosticStatus.OK else "image_info_incomplete"
        status.values = [
            KeyValue(key="frame_id", value=image.header.frame_id),
            KeyValue(key="width", value=str(image.width)),
            KeyValue(key="height", value=str(image.height)),
            KeyValue(key="encoding", value=image.encoding),
            KeyValue(key="data_bytes", value=str(len(image.data))),
        ]
        array = DiagnosticArray()
        array.header.stamp = self.get_clock().now().to_msg()
        array.status.append(status)
        self._publisher.publish(array)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CameraImageMonitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, RuntimeError):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
