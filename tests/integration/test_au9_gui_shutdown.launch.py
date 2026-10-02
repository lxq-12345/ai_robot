"""Check both AU9 shutdown paths, backend ownership and graceful exit."""
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import unittest
from urllib.parse import urlparse

import launch
import launch.actions
import launch.events
import launch_testing


def generate_test_description():
    return launch.LaunchDescription([
        launch.actions.TimerAction(period=240.0, actions=[
            launch.actions.EmitEvent(event=launch.events.Shutdown(reason='test deadline')),
        ]),
        launch_testing.actions.ReadyToTest(),
    ])


def process_identity(pid):
    try:
        stat = Path(f'/proc/{pid}/stat').read_text()
        fields = stat[stat.rindex(')') + 2:].split()
        return fields[19] if fields[0] != 'Z' else None
    except (OSError, IndexError):
        return None


def descendants(root_pid):
    parents = {}
    for directory in Path('/proc').iterdir():
        if directory.name.isdigit():
            try:
                stat = (directory / 'stat').read_text()
                fields = stat[stat.rindex(')') + 2:].split()
                parents[int(directory.name)] = int(fields[1])
            except (OSError, ValueError, IndexError):
                pass
    result = {root_pid}
    while True:
        expanded = result | {pid for pid, parent in parents.items() if parent in result}
        if expanded == result:
            return result
        result = expanded


class TestGuiShutdown(unittest.TestCase):
    def _run_session(self, interrupt):
        workspace = Path(__file__).resolve().parents[2]
        mode = 'interrupt' if interrupt else 'stop'
        runtime = workspace / 'log'
        runtime.mkdir(exist_ok=True)
        log = runtime / f'au9_shutdown_{mode}_final.log'
        stop_command = ['bash', str(workspace/'scripts/stop_au9_manual_nav2.sh')]
        port = urlparse(os.environ.get('GAZEBO_MASTER_URI', 'http://localhost:11345')).port or 11345

        def listeners():
            return subprocess.run(
                ['ss', '-H', '-ltn', 'sport', '=', f':{port}'],
                capture_output=True, text=True, check=True,
            ).stdout.strip()

        self.assertFalse(listeners(), 'Gazebo port already occupied; refusing test')
        owned = {}
        unrelated = None
        with log.open('w') as stream:
            process = subprocess.Popen(
                ['bash', str(workspace/'scripts/start_au9_manual_nav2.sh')],
                cwd=workspace, stdout=stream, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                deadline = time.monotonic()+50
                while time.monotonic() < deadline:
                    owned.update({pid: process_identity(pid) for pid in descendants(process.pid)
                                  if process_identity(pid) is not None})
                    self.assertIsNone(process.poll(), log.read_text()[-2000:])
                    output = log.read_text()
                    if ('Service response received for initialization' in output
                            and 'Managed nodes are active' in output):
                        break
                    time.sleep(0.5)
                else:
                    self.fail('RViz/Waypoint and Nav2 did not become ready')
                time.sleep(5)
                output = log.read_text()
                owned.update({pid: process_identity(pid) for pid in descendants(process.pid)
                              if process_identity(pid) is not None})
                started = re.findall(
                    r'\[([^]\n]+)\]: process started with pid \[([0-9]+)\]', output)
                self.assertTrue(started, 'Launch process records missing')
                for _, pid_text in started:
                    pid = int(pid_text)
                    identity = process_identity(pid)
                    if identity:
                        owned[pid] = identity

                # Mimic an unrelated Gazebo GUI command in its own session.
                # The old global command-line selector would also match it.
                unrelated = subprocess.Popen(
                    ['gzclient', '-c', 'import time; time.sleep(180)',
                     'libgazebo_ros_eol_gui.so'],
                    executable='/usr/bin/python3', start_new_session=True,
                )
                if interrupt:
                    # Match terminal Ctrl+C: signal the foreground wrapper
                    # group; the Launch backend has its own session.
                    os.killpg(process.pid, signal.SIGINT)
                else:
                    result = subprocess.run(
                        stop_command, cwd=workspace, capture_output=True, text=True, timeout=40)
                    stream.write(result.stdout + result.stderr)
                    stream.flush()
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(process.wait(timeout=40), 130 if interrupt else 0)
                output = log.read_text()
                self.assertNotIn('process has died', output)
                self.assertNotRegex(output, r'(?i)SIGSEGV|segmentation fault|exit code: -11|timed out')
                self.assertNotIn('Sending SIGTERM to AU9 process', output)
                self.assertNotIn("sending signal 'SIGTERM'", output)
                for label, pid in started:
                    self.assertRegex(output, re.escape(
                        f'[{label}]: process has finished cleanly [pid {pid}]'))
                for name in ('gzclient', 'rviz2', 'gzserver'):
                    matching = [(label, pid) for label, pid in started
                                if label.rsplit('-', 1)[0] == name]
                    self.assertEqual(len(matching), 1, f'{name} process record missing or ambiguous')
                for pid, identity in owned.items():
                    self.assertNotEqual(process_identity(pid), identity,
                                        f'AU9 process {pid} remains after shutdown')
                self.assertFalse(listeners(), 'Gazebo listener remains after shutdown')
                self.assertIsNone(unrelated.poll(), 'Stop affected an unrelated GUI session')
                repeated = subprocess.run(
                    stop_command, capture_output=True, text=True, timeout=40)
                self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
                self.assertIn('No AU9 manual Nav2 processes found.', repeated.stdout)
                self.assertIsNone(unrelated.poll(), 'Repeated stop affected unrelated session')
            finally:
                if unrelated is not None and unrelated.poll() is None:
                    unrelated.terminate()
                    unrelated.wait(timeout=10)
                cleanup = subprocess.run(
                    stop_command, capture_output=True, text=True, timeout=40)
                stream.write(cleanup.stdout + cleanup.stderr)
                stream.flush()
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)

    def test_01_stop_command(self):
        self._run_session(interrupt=False)

    def test_02_ctrl_c(self):
        self._run_session(interrupt=True)
