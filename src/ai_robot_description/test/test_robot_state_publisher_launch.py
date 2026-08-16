import subprocess
import time
import unittest
from pathlib import Path

import launch
import launch.actions
import launch.events
import launch_testing
import pytest
import rclpy
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node
from rcl_interfaces.srv import GetParameters
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from tf2_msgs.msg import TFMessage


@pytest.mark.launch_test
def generate_test_description():
    package_share = Path(get_package_share_directory("ai_robot_description"))
    xacro_file = package_share / "urdf" / "ai_robot.urdf.xacro"
    robot_description = subprocess.run(
        ["xacro", str(xacro_file)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description}],
        output="screen",
    )

    return (
        launch.LaunchDescription(
            [
                robot_state_publisher,
                launch_testing.actions.ReadyToTest(),
                launch.actions.TimerAction(
                    period=10.0,
                    actions=[
                        launch.actions.EmitEvent(event=launch.events.Shutdown())
                    ],
                ),
            ]
        ),
        {"robot_state_publisher": robot_state_publisher},
    )


class TestRobotStatePublisher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("test_ai_robot_description")
        self.transforms = {}
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.subscription = self.node.create_subscription(
            TFMessage,
            "/tf_static",
            self._store_transforms,
            qos,
        )

    def tearDown(self):
        self.node.destroy_node()

    def _store_transforms(self, message):
        for transform in message.transforms:
            key = (transform.header.frame_id, transform.child_frame_id)
            self.transforms[key] = transform.transform

    def _spin_until(self, predicate, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            if predicate():
                return True
        return False

    def test_robot_state_publisher_node_is_visible(self):
        visible = self._spin_until(
            lambda: "robot_state_publisher" in self.node.get_node_names()
        )

        self.assertTrue(visible, "robot_state_publisher node was not discovered")

    def test_robot_description_parameter_is_available(self):
        client = self.node.create_client(
            GetParameters,
            "/robot_state_publisher/get_parameters",
        )
        self.assertTrue(client.wait_for_service(timeout_sec=5.0))

        request = GetParameters.Request()
        request.names = ["robot_description"]
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self.node, future, timeout_sec=5.0)
        response = future.result()

        self.assertIsNotNone(response)
        self.assertIn('<robot name="ai_robot">', response.values[0].string_value)

    def test_fixed_transforms_match_model(self):
        expected = {
            ("base_footprint", "base_link"): (0.0, 0.0, 0.0),
            ("base_link", "laser_link"): (0.16, 0.0, 0.295),
            ("base_link", "camera_link"): (0.20, 0.0, 0.335),
            ("base_link", "imu_link"): (0.0, 0.0, 0.235),
        }
        received = self._spin_until(
            lambda: expected.keys() <= self.transforms.keys()
        )

        self.assertTrue(received, "did not receive all expected fixed transforms")
        for key, translation in expected.items():
            actual = self.transforms[key].translation
            self.assertAlmostEqual(actual.x, translation[0], places=6)
            self.assertAlmostEqual(actual.y, translation[1], places=6)
            self.assertAlmostEqual(actual.z, translation[2], places=6)


@launch_testing.post_shutdown_test()
class TestRobotStatePublisherShutdown(unittest.TestCase):
    def test_process_exits_cleanly(self, proc_info, robot_state_publisher):
        launch_testing.asserts.assertExitCodes(
            proc_info,
            process=robot_state_publisher,
        )
