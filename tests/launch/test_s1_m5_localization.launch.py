import time
import unittest

import launch
import launch.actions
import launch.launch_description_sources
import launch_testing
import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from tf2_msgs.msg import TFMessage


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    localization = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/localization_bringup.launch.py"
        )
    )
    return launch.LaunchDescription([localization, launch_testing.actions.ReadyToTest()]), {}


class TestS1M5Localization(unittest.TestCase):
    @classmethod
    def setUpClass(cls): rclpy.init()
    @classmethod
    def tearDownClass(cls): rclpy.shutdown()
    def setUp(self):
        self.node = rclpy.create_node("test_s1_m5_localization")
        self.maps, self.transforms = [], []
        self.initial_pose = self.node.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)
        map_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
        self.node.create_subscription(OccupancyGrid, "/map", self.maps.append, map_qos)
        self.node.create_subscription(TFMessage, "/tf", self.transforms.append, 10)
    def tearDown(self): self.node.destroy_node()
    def _spin_until(self, predicate, timeout=20.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if predicate(): return True
        return False
    def test_map_reload_and_amcl_publish_map_to_odom(self):
        self.assertTrue(self._spin_until(lambda: self.maps), "map server did not reload map")
        self.assertEqual(self.maps[-1].header.frame_id, "map")
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.068
        for _ in range(5):
            self.initial_pose.publish(pose)
            rclpy.spin_once(self.node, timeout_sec=0.1)
        self.assertTrue(self._spin_until(lambda: any(t.header.frame_id == "map" and t.child_frame_id == "odom" for m in self.transforms for t in m.transforms)), "AMCL did not publish map -> odom")

    def test_amcl_accepts_initial_pose_with_position_offset(self):
        self.assertTrue(self._spin_until(lambda: self.maps), "map server did not reload map")
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.position.x = 1.2
        pose.pose.pose.position.y = -1.0
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = pose.pose.covariance[7] = 0.64
        pose.pose.covariance[35] = 0.12
        for _ in range(5):
            self.initial_pose.publish(pose)
            rclpy.spin_once(self.node, timeout_sec=0.1)
        self.assertTrue(
            self._spin_until(
                lambda: any(
                    transform.header.frame_id == "map" and transform.child_frame_id == "odom"
                    for message in self.transforms for transform in message.transforms
                )
            ),
            "AMCL did not recover a map -> odom transform after an offset initial pose",
        )
