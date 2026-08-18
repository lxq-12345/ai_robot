import unittest

from geometry_msgs.msg import Twist

from ai_robot_sim.cmd_vel_guard import VelocityLimit, clamp_twist


class TestCmdVelGuard(unittest.TestCase):
    def test_clamp_twist_limits_forward_and_turn_rates(self):
        command = Twist()
        command.linear.x = 1.50
        command.angular.z = -2.00

        bounded = clamp_twist(command, VelocityLimit(linear=0.35, angular=1.20))

        self.assertEqual(bounded.linear.x, 0.35)
        self.assertEqual(bounded.angular.z, -1.20)

    def test_clamp_twist_preserves_in_limit_commands(self):
        command = Twist()
        command.linear.x = -0.20
        command.angular.z = 0.50

        bounded = clamp_twist(command, VelocityLimit(linear=0.35, angular=1.20))

        self.assertEqual(bounded.linear.x, -0.20)
        self.assertEqual(bounded.angular.z, 0.50)


if __name__ == "__main__":
    unittest.main()
