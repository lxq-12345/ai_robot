#!/usr/bin/env python3
"""Directly start and supervise the AU8 Gazebo and RViz2 processes."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO


WORKSPACE_DIR = Path(__file__).resolve().parent.parent
ROS_SETUP = Path("/opt/ros/humble/setup.bash")
WORKSPACE_SETUP = WORKSPACE_DIR / "install" / "setup.bash"
RVIZ_CONFIG = WORKSPACE_DIR / "config" / "rviz2" / "small_yellow_car.rviz"
GAZEBO_COMMAND = (
    "ros2",
    "launch",
    "ai_robot_sim",
    "apartment_house_bringup.launch.py",
    "gui:=true",
)
RVIZ_COMMAND = (
    "rviz2",
    "-d",
    str(RVIZ_CONFIG),
    "--ros-args",
    "-p",
    "use_sim_time:=true",
)
STABILIZATION_SECONDS = 20
RVIZ_NICE_INCREMENT = 5


@dataclass
class ManagedProcess:
    process: subprocess.Popen[bytes]
    process_group: int
    log_stream: BinaryIO | None = None
    log_path: Path | None = None


managed: dict[str, ManagedProcess] = {}
ros_environment: dict[str, str] = {}


def load_ros_environment() -> dict[str, str]:
    command = (
        "set +u; "
        f"source {ROS_SETUP}; "
        f"source {WORKSPACE_SETUP}; "
        "env -0"
    )
    result = subprocess.run(
        ["/bin/bash", "-c", command],
        cwd=WORKSPACE_DIR,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    environment: dict[str, str] = {}
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        key, value = entry.split(b"=", 1)
        environment[os.fsdecode(key)] = os.fsdecode(value)
    return environment


def process_exists(executable_name: str) -> bool:
    return (
        subprocess.run(
            ["pgrep", "-x", executable_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def gazebo_topics_ready() -> bool:
    result = subprocess.run(
        ["ros2", "topic", "list"],
        cwd=WORKSPACE_DIR,
        env=ros_environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=5,
    )
    topics = set(result.stdout.splitlines())
    return {"/camera/image_raw", "/camera/right/image_raw"}.issubset(topics)


def wait_for_gazebo_ready(current: ManagedProcess, timeout: int = 45) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        return_code = current.process.poll()
        if return_code is not None:
            raise RuntimeError(
                f"Gazebo launch exited during startup (exit code {return_code})."
            )
        if process_exists("gzclient") and gazebo_topics_ready():
            print("Gazebo and both AU8 camera topics are ready.")
            return
        time.sleep(1)
    raise RuntimeError("Gazebo and both camera topics were not ready within 45 seconds.")


def wait_for_runtime_stability(seconds: int = STABILIZATION_SECONDS) -> None:
    active = {
        name: current
        for name, current in managed.items()
        if current.process.poll() is None
    }
    if not active:
        return

    names = " and ".join(active)
    print(f"Waiting {seconds} seconds for {names} to stabilize...")
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        for name, current in active.items():
            return_code = current.process.poll()
            if return_code is not None:
                raise RuntimeError(
                    f"{name} exited during stabilization (exit code {return_code})."
                )
        time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
    print(f"{names} stabilization period completed.")


def start_gazebo() -> None:
    if process_exists("gzserver") or process_exists("gzclient"):
        raise RuntimeError(
            "Gazebo is already running. Stop the existing Gazebo session first."
        )

    log_dir = WORKSPACE_DIR / "log" / "manual"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"au8_gazebo_python_{timestamp}.log"
    log_stream = log_path.open("ab", buffering=0)

    print("Starting AU8 Gazebo directly with ros2 launch...")
    print(f"Gazebo log: {log_path}")
    try:
        process = subprocess.Popen(
            GAZEBO_COMMAND,
            cwd=WORKSPACE_DIR,
            env=ros_environment,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except BaseException:
        log_stream.close()
        raise

    current = ManagedProcess(
        process=process,
        process_group=os.getpgid(process.pid),
        log_stream=log_stream,
        log_path=log_path,
    )
    managed["gazebo"] = current

    try:
        wait_for_gazebo_ready(current)
    except BaseException:
        stop("gazebo")
        raise

    print(f"gazebo started (PID {process.pid}).")
    if "rviz2" in managed and managed["rviz2"].process.poll() is None:
        wait_for_runtime_stability()


def start_rviz2() -> None:
    if process_exists("rviz2"):
        raise RuntimeError(
            "RViz2 is already running. Stop the existing RViz2 session first."
        )

    print(
        "Starting AU8 RViz2 directly "
        f"with nice +{RVIZ_NICE_INCREMENT} to preserve Gazebo sensor throughput..."
    )
    process = subprocess.Popen(
        RVIZ_COMMAND,
        cwd=WORKSPACE_DIR,
        env=ros_environment,
        preexec_fn=lambda: os.nice(RVIZ_NICE_INCREMENT),
        start_new_session=True,
    )
    current = ManagedProcess(
        process=process,
        process_group=os.getpgid(process.pid),
    )
    managed["rviz2"] = current

    time.sleep(1)
    return_code = process.poll()
    if return_code is not None:
        managed.pop("rviz2", None)
        raise RuntimeError(f"RViz2 failed to start (exit code {return_code}).")

    print(f"rviz2 started (PID {process.pid}).")
    wait_for_runtime_stability()


def start(name: str) -> None:
    current = managed.get(name)
    if current is not None and current.process.poll() is None:
        print(f"{name} is already running.")
        return
    if name == "gazebo":
        start_gazebo()
    elif name == "rviz2":
        start_rviz2()
    else:
        raise ValueError(f"Unknown managed process: {name}")


def process_group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    return True


def send_group_signal(process_group: int, signal_number: signal.Signals) -> None:
    try:
        os.killpg(process_group, signal_number)
    except ProcessLookupError:
        pass


def wait_for_group_exit(current: ManagedProcess, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current.process.poll()
        if not process_group_exists(current.process_group):
            return True
        time.sleep(0.25)
    return not process_group_exists(current.process_group)


def close_log(current: ManagedProcess) -> None:
    if current.log_stream is not None and not current.log_stream.closed:
        current.log_stream.close()


def stop(name: str) -> None:
    current = managed.pop(name, None)
    if current is None:
        print(f"{name} is not managed by this program.")
        return

    try:
        if not process_group_exists(current.process_group):
            current.process.poll()
            print(f"{name} has already stopped.")
            return

        print(f"Stopping {name} process group with SIGINT...")
        send_group_signal(current.process_group, signal.SIGINT)
        if not wait_for_group_exit(current, 12):
            print(f"{name} did not stop after SIGINT; sending SIGTERM.")
            send_group_signal(current.process_group, signal.SIGTERM)
            if not wait_for_group_exit(current, 5):
                print(f"{name} did not stop after SIGTERM; sending SIGKILL.")
                send_group_signal(current.process_group, signal.SIGKILL)
                wait_for_group_exit(current, 3)
        current.process.poll()
        print(f"{name} stopped.")
    finally:
        close_log(current)


def restart(name: str) -> None:
    stop(name)
    start(name)


def shutdown() -> None:
    # Stop the display first, then the simulator that supplies its data.
    stop("rviz2")
    stop("gazebo")


def raise_keyboard_interrupt(_signal_number: int, _frame: object | None) -> None:
    raise KeyboardInterrupt


def print_help() -> None:
    print(
        "\nCommands:\n"
        "  g  restart Gazebo while keeping RViz2 running\n"
        "  s  stop Gazebo only\n"
        "  a  start Gazebo\n"
        "  r  restart RViz2\n"
        "  h  show this help\n"
        "  q  stop both programs and quit\n"
    )


def validate_prerequisites() -> None:
    missing = [
        str(path)
        for path in (ROS_SETUP, WORKSPACE_SETUP, RVIZ_CONFIG)
        if not path.is_file()
    ]
    if missing:
        raise RuntimeError(f"Missing AU8 prerequisite: {', '.join(missing)}")
    if not os.environ.get("DISPLAY"):
        raise RuntimeError(
            "DISPLAY is not set; run this program from the graphical desktop."
        )


def main() -> int:
    global ros_environment

    if len(sys.argv) != 1:
        print(f"Usage: {Path(sys.argv[0]).name}", file=sys.stderr)
        return 2

    signal.signal(signal.SIGTERM, raise_keyboard_interrupt)

    try:
        validate_prerequisites()
        ros_environment = load_ros_environment()
        start("gazebo")
        start("rviz2")
        print_help()

        while True:
            command = input("AU8> ").strip().lower()
            if command == "g":
                restart("gazebo")
            elif command == "s":
                stop("gazebo")
            elif command == "a":
                start("gazebo")
            elif command == "r":
                restart("rviz2")
            elif command == "h":
                print_help()
            elif command == "q":
                break
            elif command:
                print("Unknown command. Enter h for help.")
    except (EOFError, KeyboardInterrupt):
        print("\nStopping AU8...")
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    finally:
        shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
