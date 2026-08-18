import math
import time
import unittest

import launch
import launch.actions
import launch.launch_description_sources
import launch_testing
import rclpy
from ament_index_python.packages import get_package_share_directory
from gazebo_msgs.srv import DeleteEntity, SpawnEntity
from geometry_msgs.msg import PoseWithCovarianceStamped
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import Odometry
from nav2_msgs.msg import Costmap
from sensor_msgs.msg import LaserScan


OBSTACLE_SDF = """
<sdf version="1.6">
  <model name="s1_m5_temporary_obstacle">
    <static>true</static>
    <link name="body">
      <collision name="collision">
        <geometry><box><size>0.3 0.3 0.8</size></box></geometry>
      </collision>
      <visual name="visual">
        <geometry><box><size>0.3 0.3 0.8</size></box></geometry>
      </visual>
    </link>
  </model>
</sdf>
"""


def generate_test_description():
    sim_share = get_package_share_directory("ai_robot_sim")
    nav2 = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f"{sim_share}/launch/nav2_bringup.launch.py"
        )
    )
    return launch.LaunchDescription([nav2, launch_testing.actions.ReadyToTest()]), {}


class TestS1M5TemporaryObstacle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_s1_m5_temporary_obstacle")
        self.scans = []
        self.costmaps = []
        self.odom = []
        self.initial_pose = self.node.create_publisher(
            PoseWithCovarianceStamped, "/initialpose", 10
        )
        self.node.create_subscription(LaserScan, "/scan", self.scans.append, 10)
        self.node.create_subscription(
            Costmap, "/local_costmap/costmap_raw", self.costmaps.append, 10
        )
        self.node.create_subscription(Odometry, "/odom", self.odom.append, 10)
        self.spawn = self.node.create_client(SpawnEntity, "/spawn_entity")
        self.delete = self.node.create_client(DeleteEntity, "/delete_entity")
        self.smoother_state = self.node.create_client(
            GetState, "/velocity_smoother/get_state"
        )

    def tearDown(self):
        if self.delete.wait_for_service(timeout_sec=0.2):
            request = DeleteEntity.Request()
            request.name = "s1_m5_temporary_obstacle"
            future = self.delete.call_async(request)
            self._spin_until(lambda: future.done(), timeout=2.0)
        self.node.destroy_node()

    def _spin_until(self, predicate, timeout=30.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if predicate():
                return True
        return False

    def _smoother_is_active(self):
        if not self.smoother_state.wait_for_service(timeout_sec=0.1):
            return False
        future = self.smoother_state.call_async(GetState.Request())
        if not self._spin_until(lambda: future.done(), timeout=2.0):
            return False
        return future.result().current_state.id == State.PRIMARY_STATE_ACTIVE

    def _minimum_range(self):
        if not self.scans:
            return math.inf
        finite = [
            value
            for value in self.scans[-1].ranges
            if math.isfinite(value) and value > self.scans[-1].range_min
        ]
        return min(finite, default=math.inf)

    def _occupied_cells(self):
        if not self.costmaps:
            return 0
        return sum(value >= 253 for value in self.costmaps[-1].data)

    def test_temporary_obstacle_reaches_and_clears_local_costmap(self):
        self.assertTrue(self._spin_until(lambda: self.odom), "Gazebo odometry unavailable")
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.orientation.w = 1.0
        pose.pose.covariance[0] = pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.068
        for _ in range(5):
            self.initial_pose.publish(pose)
            rclpy.spin_once(self.node, timeout_sec=0.1)
        self.assertTrue(
            self._spin_until(self._smoother_is_active, timeout=30.0),
            "navigation stack did not become active",
        )
        self.assertTrue(
            self._spin_until(lambda: self.scans and self.costmaps),
            "scan or local costmap unavailable",
        )
        baseline_cells = self._occupied_cells()

        self.assertTrue(
            self.spawn.wait_for_service(timeout_sec=10.0),
            "Gazebo spawn service unavailable",
        )
        request = SpawnEntity.Request()
        request.name = "s1_m5_temporary_obstacle"
        request.xml = OBSTACLE_SDF
        request.initial_pose.position.x = 0.45
        request.initial_pose.position.y = -0.40
        request.initial_pose.position.z = 0.40
        request.initial_pose.orientation.w = 1.0
        request.reference_frame = "world"
        future = self.spawn.call_async(request)
        self.assertTrue(self._spin_until(lambda: future.done(), timeout=10.0))
        self.assertTrue(future.result().success, future.result().status_message)

        self.assertTrue(
            self._spin_until(lambda: self._minimum_range() < 0.38, timeout=5.0),
            "laser did not detect the temporary obstacle",
        )
        self.assertTrue(
            self._spin_until(
                lambda: self._occupied_cells() > baseline_cells + 2, timeout=5.0
            ),
            "temporary obstacle did not enter the Nav2 local costmap",
        )

        delete = DeleteEntity.Request()
        delete.name = "s1_m5_temporary_obstacle"
        future = self.delete.call_async(delete)
        self.assertTrue(self._spin_until(lambda: future.done(), timeout=5.0))
        self.assertTrue(future.result().success, future.result().status_message)
        self.assertTrue(
            self._spin_until(
                lambda: self._minimum_range() > 0.40
                and self._occupied_cells() <= baseline_cells + 2,
                timeout=8.0,
            ),
            "temporary obstacle did not clear from scan and local costmap",
        )
