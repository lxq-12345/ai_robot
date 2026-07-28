import time
import unittest

import launch
import launch.actions
import launch.launch_description_sources
import launch_ros.actions
import launch_testing
import rclpy
from ament_index_python.packages import get_package_share_directory
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, Image, LaserScan
from tf2_msgs.msg import TFMessage


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    bringup = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/sim_bringup.launch.py"
        )
    )
    scan_monitor = launch_ros.actions.Node(
        package="ai_robot_sim",
        executable="scan_obstacle_monitor",
        output="screen",
    )
    camera_monitor = launch_ros.actions.Node(
        package="ai_robot_sim",
        executable="camera_image_monitor",
        output="screen",
    )

    return launch.LaunchDescription(
        [
            bringup,
            scan_monitor,
            camera_monitor,
            launch_testing.actions.ReadyToTest(),
        ]
    ), {"scan_monitor": scan_monitor, "camera_monitor": camera_monitor}


class TestS1M4SensorProcessing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_s1_m4_sensor_processing")
        self.scan_messages = []
        self.image_messages = []
        self.camera_info_messages = []
        self.diagnostics = []
        self.tf_messages = []
        tf_static_qos = QoSProfile(
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.node.create_subscription(LaserScan, "/scan", self.scan_messages.append, 10)
        self.node.create_subscription(Image, "/camera/image_raw", self.image_messages.append, 10)
        self.node.create_subscription(CameraInfo, "/camera/camera_info", self.camera_info_messages.append, 10)
        self.node.create_subscription(DiagnosticArray, "/diagnostics", self.diagnostics.append, 10)
        self.node.create_subscription(TFMessage, "/tf_static", self.tf_messages.append, tf_static_qos)

    def tearDown(self):
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=15.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.10)
            if predicate():
                return True
        return False

    def _diagnostic_status(self, name):
        for array in reversed(self.diagnostics):
            for status in array.status:
                if status.name == name:
                    return status
        return None

    def _has_static_tf(self, parent, child):
        for message in self.tf_messages:
            for transform in message.transforms:
                if transform.header.frame_id == parent and transform.child_frame_id == child:
                    return True
        return False

    def test_scan_obstacle_and_camera_processing_chains_publish_diagnostics(self):
        self.assertTrue(self._spin_until(lambda: self.scan_messages), "missing /scan")
        self.assertTrue(self._spin_until(lambda: self.image_messages), "missing /camera/image_raw")
        self.assertTrue(self._spin_until(lambda: self.camera_info_messages), "missing /camera/camera_info")
        self.assertTrue(self._spin_until(lambda: self._has_static_tf("base_link", "laser_link")), "missing laser TF")
        self.assertTrue(self._spin_until(lambda: self._has_static_tf("base_link", "camera_link")), "missing camera TF")

        scan_status = self._spin_until(
            lambda: self._diagnostic_status("s1_m4.scan_obstacle_chain") is not None
        )
        camera_status = self._spin_until(
            lambda: self._diagnostic_status("s1_m4.camera_image_chain") is not None
        )
        self.assertTrue(scan_status, "scan obstacle chain did not publish diagnostics")
        self.assertTrue(camera_status, "camera image chain did not publish diagnostics")

        scan_diag = self._diagnostic_status("s1_m4.scan_obstacle_chain")
        camera_diag = self._diagnostic_status("s1_m4.camera_image_chain")
        self.assertIn(scan_diag.level, (DiagnosticStatus.OK, DiagnosticStatus.WARN))
        self.assertEqual(camera_diag.level, DiagnosticStatus.OK)
        self.assertEqual(dict((item.key, item.value) for item in scan_diag.values)["frame_id"], "laser_link")
        self.assertEqual(dict((item.key, item.value) for item in camera_diag.values)["frame_id"], "camera_link")


@launch_testing.post_shutdown_test()
class TestS1M4SensorProcessingShutdown(unittest.TestCase):
    def test_processing_nodes_exit_cleanly(self, proc_info, scan_monitor, camera_monitor):
        launch_testing.asserts.assertExitCodes(proc_info, process=scan_monitor)
        launch_testing.asserts.assertExitCodes(proc_info, process=camera_monitor)
