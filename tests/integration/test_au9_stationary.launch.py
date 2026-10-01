"""AU9 zero-command creep and scan/map alignment regression (simulation only)."""
import json
import os
from pathlib import Path
import subprocess
import unittest

import launch
import launch.actions
import launch.launch_description_sources
import launch_testing
from ament_index_python.packages import get_package_share_directory


def generate_test_description():
    share = get_package_share_directory('ai_robot_sim')
    simulation = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            f'{share}/launch/apartment_nav2_bringup.launch.py'),
        launch_arguments={'gui': 'false', 'rviz': 'false'}.items(),
    )
    return launch.LaunchDescription([simulation, launch_testing.actions.ReadyToTest()])


class TestStationary(unittest.TestCase):
    def test_zero_command_stability_and_scan_alignment(self):
        workspace = Path(__file__).resolve().parents[2]
        output = workspace / os.environ.get(
            'AU9_STATIONARY_EVIDENCE', 'log/au9_stationary_regression.jsonl')
        completed = subprocess.run(
            ['/usr/bin/python3', str(workspace/'scripts/measure_au9_stationary.py'),
             str(output), '--seconds', '60', '--settle', '10'],
            check=True, capture_output=True, text=True, timeout=130,
        )
        print(completed.stdout)
        result = json.loads(output.with_suffix('.summary.json').read_text())
        self.assertGreaterEqual(result['samples'], 55)
        self.assertGreater(result['sim_duration'], 30)
        self.assertEqual(result['max_safe_command'], 0)
        self.assertLess(result['max_displacement_m'], 0.002)
        self.assertLess(result['max_yaw_change_rad'], 0.00174533)
        self.assertLess(result['max_wheel_rad_s'], 0.001)
        self.assertLess(result['map_odom_excursion_m'], 0.002)
        self.assertLess(result['map_odom_yaw_excursion_rad'], 0.00174533)
        self.assertGreater(result['scan_endpoint_count'], 100)
        self.assertLess(result['scan_wall_median_m'], 0.05)
        self.assertGreater(result['scan_wall_fraction_within_0_1m'], 0.90)
