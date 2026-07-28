import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "ai_robot_py_example"))

from ai_robot_py_example.baseline_node import status_line


class TestPythonExample(unittest.TestCase):
    def test_status_line(self):
        self.assertEqual(status_line("ready"), "ai_robot_py_example:ready")


if __name__ == "__main__":
    unittest.main()
