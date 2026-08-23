import math
import time
import unittest

import launch
import launch.actions
import launch.launch_description_sources
import launch_testing
import rclpy
from ament_index_python.packages import get_package_share_directory
from sensor_msgs.msg import CameraInfo, Image, Imu, JointState, LaserScan


WHEEL_JOINTS = {
    "left_front_wheel_joint",
    "left_rear_wheel_joint",
    "right_front_wheel_joint",
    "right_rear_wheel_joint",
}


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    bringup = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/sim_bringup.launch.py"
        )
    )

    return launch.LaunchDescription(
        [
            bringup,
            launch_testing.actions.ReadyToTest(),
        ]
    ), {}


class TestSimSensors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_sim_sensors")
        self.scan_messages = []
        self.image_messages = []
        self.camera_info_messages = []
        self.imu_messages = []
        self.joint_state_messages = []
        self.node.create_subscription(LaserScan, "/scan", self.scan_messages.append, 10)
        self.node.create_subscription(Image, "/camera/image_raw", self.image_messages.append, 10)
        self.node.create_subscription(CameraInfo, "/camera/camera_info", self.camera_info_messages.append, 10)
        self.node.create_subscription(Imu, "/imu/data", self.imu_messages.append, 10)
        self.node.create_subscription(JointState, "/joint_states", self.joint_state_messages.append, 10)

    def tearDown(self):
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=18.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.10)
            if predicate():
                return True
        return False

    def test_simulated_sensor_topics_publish_valid_messages(self):
        self.assertTrue(self._spin_until(lambda: self.scan_messages), "missing /scan")
        self.assertTrue(self._spin_until(lambda: self.image_messages), "missing /camera/image_raw")
        self.assertTrue(self._spin_until(lambda: self.camera_info_messages), "missing /camera/camera_info")
        self.assertTrue(self._spin_until(lambda: self.imu_messages), "missing /imu/data")
        self.assertTrue(self._spin_until(lambda: self.joint_state_messages), "missing /joint_states")

        scan = self.scan_messages[-1]
        self.assertEqual(scan.header.frame_id, "laser_link")
        self.assertEqual(len(scan.ranges), 360)
        self.assertLess(scan.angle_min, 0.0)
        self.assertGreater(scan.angle_max, 0.0)
        self.assertAlmostEqual(scan.range_min, 0.12, places=2)
        self.assertAlmostEqual(scan.range_max, 8.0, places=1)

        image = self.image_messages[-1]
        self.assertEqual(image.header.frame_id, "camera_link")
        self.assertEqual(image.width, 640)
        self.assertEqual(image.height, 480)
        self.assertIn(image.encoding, ("rgb8", "bgr8", "rgba8", "bgra8"))
        self.assertGreater(len(image.data), 0)

        camera_info = self.camera_info_messages[-1]
        self.assertEqual(camera_info.header.frame_id, "camera_link")
        self.assertEqual(camera_info.width, 640)
        self.assertEqual(camera_info.height, 480)

        imu = self.imu_messages[-1]
        self.assertEqual(imu.header.frame_id, "imu_link")
        self.assertNotEqual(imu.orientation_covariance[0], -1.0)
        self.assertTrue(math.isfinite(imu.orientation.w))
        self.assertTrue(math.isfinite(imu.angular_velocity.z))
        self.assertTrue(math.isfinite(imu.linear_acceleration.z))

        joint_state = self.joint_state_messages[-1]
        self.assertTrue(WHEEL_JOINTS <= set(joint_state.name))
        self.assertGreaterEqual(len(joint_state.position), 4)
        self.assertGreaterEqual(len(joint_state.velocity), 4)
