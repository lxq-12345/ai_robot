"""AU9 orphan cleanup must use saved identity and leave other sessions alive."""
import json
from pathlib import Path
import subprocess
import unittest


class TestStopOwnership(unittest.TestCase):
    def test_orphan_and_repeated_stop(self):
        workspace = Path(__file__).resolve().parents[2]
        state = workspace / 'log/au9_session.json'
        self.assertFalse(state.exists(), 'Existing AU9 record; refusing isolated test')
        # A session leader exits while its child retains the session identity.
        parent = subprocess.Popen([
            '/usr/bin/python3', '-c',
            'import subprocess; from pathlib import Path; '
            's=Path("/proc/self/stat").read_text(); '
            'print(s[s.rindex(")")+2:].split()[19], flush=True); '
            'p=subprocess.Popen(["sleep", "120"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print(p.pid, flush=True)',
        ], stdout=subprocess.PIPE, text=True, start_new_session=True)
        output, _ = parent.communicate(timeout=5)
        started, child_pid = output.splitlines()
        child_pid = int(child_pid)
        unrelated = subprocess.Popen(['sleep', '120'], start_new_session=True)
        try:
            state.write_text(json.dumps(dict(
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                root_pid=parent.pid, root_started=started, session=parent.pid, owned=[])))
            result = subprocess.run(['bash', str(workspace/'scripts/stop_au9_manual_nav2.sh')],
                                    capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('Recovering orphaned AU9 processes', result.stdout)
            stat = Path(f'/proc/{child_pid}/stat')
            if stat.exists():
                text = stat.read_text()
                self.assertEqual(text[text.rindex(')')+2:].split()[0], 'Z')
            self.assertIsNone(unrelated.poll())
            self.assertFalse(state.exists())
            result = subprocess.run(['bash', str(workspace/'scripts/stop_au9_manual_nav2.sh')],
                                    capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('No AU9 manual Nav2 processes found.', result.stdout)
            self.assertIsNone(unrelated.poll())
        finally:
            import os
            import signal
            try:
                os.kill(child_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            unrelated.terminate()
            unrelated.wait(timeout=5)
            state.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
