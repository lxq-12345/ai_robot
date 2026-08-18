import time
import tempfile
import unittest
from pathlib import Path

import launch
import launch.actions
import launch.launch_description_sources
import launch_testing
import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid
from nav2_msgs.srv import SaveMap
from tf2_msgs.msg import TFMessage


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    slam = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/slam_bringup.launch.py"
        )
    )
    return launch.LaunchDescription([slam, launch_testing.actions.ReadyToTest()]), {}


class TestS1M5Slam(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_s1_m5_slam")
        self.maps = []
        self.tf_messages = []
        self.publisher = self.node.create_publisher(Twist, "/cmd_vel_raw", 10)
        self.node.create_subscription(OccupancyGrid, "/map", self.maps.append, 10)
        self.node.create_subscription(TFMessage, "/tf", self.tf_messages.append, 10)
        self.save_map_client = self.node.create_client(SaveMap, "/map_saver/save_map")

    def tearDown(self):
        self.publisher.publish(Twist())
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=20.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if predicate():
                return True
        return False

    def test_slam_publishes_map_and_map_to_odom_tf(self):
        self.assertTrue(self._spin_until(lambda: self.maps), "missing /map")
        command = Twist()
        command.linear.x = 0.15
        for _ in range(12):
            self.publisher.publish(command)
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.assertTrue(self._spin_until(lambda: self.maps[-1].info.width > 10), "invalid map")
        self.assertTrue(
            self._spin_until(
                lambda: any(
                    transform.header.frame_id == "map" and transform.child_frame_id == "odom"
                    for message in self.tf_messages for transform in message.transforms
                )
            ),
            "missing map -> odom TF",
        )

    def test_slam_map_can_be_saved_for_localization_reload(self):
        self.assertTrue(self._spin_until(lambda: self.maps), "missing /map")
        self.assertTrue(
            self.save_map_client.wait_for_service(timeout_sec=10.0),
            "missing Nav2 map save service",
        )
        output_dir = Path(tempfile.mkdtemp(prefix="ai_robot_s1_m5_map_"))
        map_base = output_dir / "navigation_map"
        request = SaveMap.Request()
        request.map_topic = "/map"
        request.map_url = str(map_base)
        request.image_format = "pgm"
        request.map_mode = "trinary"
        request.free_thresh = 0.25
        request.occupied_thresh = 0.65
        future = self.save_map_client.call_async(request)
        self.assertTrue(self._spin_until(lambda: future.done(), timeout=10.0), "map save timed out")
        self.assertTrue(future.result().result, "map saver rejected the SLAM map")
        self.assertTrue((map_base.with_suffix(".yaml")).is_file(), "missing saved map YAML")
        self.assertTrue((map_base.with_suffix(".pgm")).is_file(), "missing saved map image")
