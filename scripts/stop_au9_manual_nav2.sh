#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if (( $# != 0 )); then
  echo "Usage: $0" >&2
  exit 2
fi

# Serialise external stop and the start script's EXIT cleanup. No unrelated
# GUI is selected by name. The lock lives in the ignored runtime directory.
mkdir -p "${workspace_dir}/log"
exec 9>"${workspace_dir}/log/au9_shutdown.lock"
flock -x 9
/usr/bin/python3 - "$workspace_dir" <<'STOP_PY'
import json
import os
from pathlib import Path
import signal
import sys
import time

workspace = Path(sys.argv[1]).resolve()


def read_process(pid):
    try:
        directory = Path('/proc') / str(pid)
        stat = (directory / 'stat').read_text()
        name = stat[stat.index('(') + 1:stat.rindex(')')]
        fields = stat[stat.rindex(')') + 2:].split()
        return dict(pid=pid, name=name, state=fields[0], parent=int(fields[1]),
                    session=int(fields[3]), started=fields[19])
    except (OSError, ValueError, IndexError):
        return None


def snapshot():
    result = {}
    for directory in Path('/proc').iterdir():
        if directory.name.isdigit():
            process = read_process(int(directory.name))
            if process:
                result[process['pid']] = process
    return result


def is_au9_launch(process):
    try:
        directory = Path('/proc') / str(process['pid'])
        arguments = (directory / 'cmdline').read_bytes().split(bytes([0]))
        # The ros2 executable can be invoked directly or through Python.
        for index in (0, 1):
            if len(arguments) > index + 3 and Path(os.fsdecode(arguments[index])).name == 'ros2':
                if arguments[index + 1:index + 4] == [
                        b'launch', b'ai_robot_sim', b'apartment_nav2_bringup.launch.py']:
                    return directory.joinpath('cwd').resolve() == workspace
    except (OSError, ValueError):
        pass
    return False


def is_workspace_backend(process):
    # With Launch gone, only accept the exact installed AU9 world and cwd.
    # Never infer ownership from a global process name or a stale PID.
    try:
        directory = Path('/proc') / str(process['pid'])
        arguments = (directory / 'cmdline').read_bytes().split(bytes([0]))
        world = workspace / 'install/ai_robot_sim/share/ai_robot_sim/worlds/apartment_v1.3.world'
        return (process['state'] != 'Z' and arguments
                and Path(os.fsdecode(arguments[0])).name == 'gzserver'
                and os.fsencode(world) in arguments
                and directory.joinpath('cwd').resolve() == workspace)
    except (OSError, ValueError):
        return False


processes = snapshot()
roots = [process for process in processes.values() if is_au9_launch(process)]
state_file = workspace / 'log/au9_session.json'
boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
if len(roots) > 1:
    print('ERROR: Multiple AU9 Launch sessions found; refusing ambiguous shutdown.', file=sys.stderr)
    sys.exit(1)

orphan = not roots
if roots:
    root = roots[0]
    owned = {root['pid']: root}
else:
    owned = {}
    root = None
    if state_file.exists():
        try:
            record = json.loads(state_file.read_text())
            if record['boot_id'] == boot_id:
                for process in processes.values():
                    if (process['session'] == record['session'] == record['root_pid']
                            and int(process['started']) >= int(record['root_started'])
                            and process['state'] != 'Z'):
                        owned[process['pid']] = process
                for saved in record['owned']:
                    current = processes.get(saved['pid'])
                    if current and current['started'] == saved['started']:
                        owned[current['pid']] = current
        except (OSError, ValueError, KeyError, TypeError):
            print('ERROR: Invalid AU9 ownership record; refusing shutdown.', file=sys.stderr)
            sys.exit(1)
    if not owned:
        # Never claim success for a recognizable but unowned apartment backend.
        world = workspace / 'install/ai_robot_sim/share/ai_robot_sim/worlds/apartment_v1.3.world'
        for process in processes.values():
            try:
                directory = Path('/proc') / str(process['pid'])
                arguments = directory.joinpath('cmdline').read_bytes().split(bytes([0]))
                if (process['state'] != 'Z' and process['name'] == 'gzserver'
                        and os.fsencode(world) in arguments
                        and directory.joinpath('cwd').resolve() == workspace):
                    print('ERROR: Apartment gzserver remains without AU9 ownership; '
                          'refusing unverified cleanup.', file=sys.stderr)
                    sys.exit(1)
            except OSError:
                pass
        state_file.unlink(missing_ok=True)
        print('No AU9 manual Nav2 processes found.', flush=True)
        sys.exit(0)
    print('Recovering orphaned AU9 processes from saved session identity.', flush=True)


def refresh_owned():
    processes = snapshot()
    # A dedicated session identifies children reparented during shutdown.
    if root is not None and root['session'] == root['pid']:
        for pid, process in processes.items():
            if process['session'] == root['session']:
                owned.setdefault(pid, process)
    changed = True
    while changed:
        changed = False
        for pid, process in processes.items():
            parent = owned.get(process['parent'])
            live_parent = processes.get(process['parent'])
            if (pid not in owned and parent and live_parent
                    and parent['started'] == live_parent['started']):
                owned[pid] = process
                changed = True


def running(process):
    current = read_process(process['pid'])
    return (current is not None and current['state'] != 'Z'
            and current['started'] == process['started'])


def send(processes, sig):
    for process in processes:
        if running(process):
            print(f"Sending {sig.name} to AU9 process {process['pid']} ({process['name']}).", flush=True)
            try:
                os.kill(process['pid'], sig)
            except ProcessLookupError:
                pass


def wait_for_exit(processes, timeout, refresh=False):
    deadline = time.monotonic() + timeout
    while True:
        if refresh:
            refresh_owned()
            processes = list(owned.values())
        if not any(running(process) for process in processes):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)


refresh_owned()
if root is not None:
    record = dict(boot_id=boot_id, root_pid=root['pid'],
                  root_started=root['started'], session=root['session'],
                  owned=list(owned.values()))
    temporary = state_file.with_suffix('.tmp')
    temporary.write_text(json.dumps(record))
    temporary.replace(state_file)
gui = [process for process in owned.values() if process['name'] in ('rviz2', 'gzclient')]
abnormal = False
send(gui, signal.SIGINT)
if not wait_for_exit(gui, 10):
    abnormal = True
    print('ERROR: GUI shutdown timed out; sending SIGTERM to remaining GUI clients.', file=sys.stderr)
    send(gui, signal.SIGTERM)
    wait_for_exit(gui, 5)

# Launch owns backend termination. Do not signal its children in normal exit.
send(list(owned.values()) if orphan else [root], signal.SIGINT)
if not wait_for_exit(list(owned.values()), 15, refresh=True):
    abnormal = True
    print('ERROR: Graceful shutdown timed out; sending SIGTERM to remaining AU9 processes.', file=sys.stderr)
    send(list(owned.values()), signal.SIGTERM)
    if not wait_for_exit(list(owned.values()), 5, refresh=True):
        print('ERROR: AU9 processes remain after shutdown.', file=sys.stderr)
        sys.exit(1)

if abnormal:
    print('ERROR: AU9 required fallback termination; graceful shutdown failed.', file=sys.stderr)
    sys.exit(1)
state_file.unlink(missing_ok=True)
print('AU9 manual Nav2 processes stopped gracefully.', flush=True)
STOP_PY
