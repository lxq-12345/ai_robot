import time
import unittest

import launch
import launch.actions
import launch.launch_description_sources
import launch_ros.actions
import launch_testing
import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    bringup = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/sim_bringup.launch.py"
        )
    )
    ekf = launch_ros.actions.Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node",
        parameters=[f"{sim_share}/config/ekf_sim.yaml"],
        output="screen",
    )

    return launch.LaunchDescription(
        [bringup, ekf, launch_testing.actions.ReadyToTest()]
    ), {"ekf": ekf}


class TestS1M4EkfFusion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_s1_m4_ekf_fusion")
        self.odom_messages = []
        self.imu_messages = []
        self.filtered_messages = []
        self.publisher = self.node.create_publisher(Twist, "/cmd_vel_raw", 10)
        self.node.create_subscription(Odometry, "/odom", self.odom_messages.append, 10)
        self.node.create_subscription(Imu, "/imu/data", self.imu_messages.append, 10)
        self.node.create_subscription(
            Odometry, "/odometry/filtered", self.filtered_messages.append, 10
        )

    def tearDown(self):
        stop = Twist()
        for _ in range(5):
            self.publisher.publish(stop)
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=15.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.10)
            if predicate():
                return True
        return False

    def test_encoder_imu_ekf_publishes_fused_odometry(self):
        self.assertTrue(self._spin_until(lambda: self.odom_messages), "missing /odom")
        self.assertTrue(self._spin_until(lambda: self.imu_messages), "missing /imu/data")
        self.assertTrue(
            self._spin_until(lambda: self.filtered_messages),
            "EKF did not publish /odometry/filtered",
        )

        start_x = self.filtered_messages[-1].pose.pose.position.x
        command = Twist()
        command.linear.x = 0.20
        for _ in range(10):
            self.publisher.publish(command)
            rclpy.spin_once(self.node, timeout_sec=0.05)

        self.assertTrue(
            self._spin_until(
                lambda: self.filtered_messages[-1].pose.pose.position.x > start_x + 0.02
            ),
            "fused odometry did not reflect encoder and IMU driven motion",
        )
        latest = self.filtered_messages[-1]
        self.assertEqual(latest.header.frame_id, "odom")
        self.assertEqual(latest.child_frame_id, "base_link")


@launch_testing.post_shutdown_test()
class TestS1M4EkfFusionShutdown(unittest.TestCase):
    def test_ekf_exits_cleanly(self, proc_info, ekf):
        launch_testing.asserts.assertExitCodes(proc_info, process=ekf)
