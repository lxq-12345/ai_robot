# AI Robot

This repository is the ROS 2 workspace for an indoor differential-drive mobile robot. The active milestone is `S1-1-M0`, the engineering and management baseline.

## Scope

- Phase 1: ROS 2 robot development.
- Phase 2: AI Agent development, after `S1-2-G1` only.
- No AI model integration, AI Agent implementation, or physical robot operation is included in `S1-1-M0`.

## Prerequisites

- Ubuntu 22.04
- ROS 2 Humble
- `colcon`
- Gazebo Classic and RViz2 for simulation verification

## Workspace Layout

```text
src/        ROS 2 packages
config/     runtime configuration
scripts/    environment, build, and test entry points
tests/      workspace-level checks
resources/  maps, models, and other resources
```

## Commands

Run all commands from the repository root:

```bash
./scripts/check_environment.sh
./scripts/build.sh
./scripts/test.sh
```

Build artifacts are generated in `build/`, `install/`, and `log/`; they are intentionally not tracked by Git.

## Safety

Physical robot power-on, motion, control commands, and hardware testing require explicit authorization for the current task. `S1-1-G1` must pass before physical robot development, and `S1-2-G1` must pass before Phase 2 or AI Agent work.
