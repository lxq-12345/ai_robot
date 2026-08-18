# AI Robot

This repository is the ROS 2 workspace for an indoor differential-drive mobile robot. Simulation milestones `S1-1-M0` through `S1-1-M6` are complete; the current work follows the M-aligned ROS 2 learning plan before `S1-1-G1`.

## Scope

- Phase 1: ROS 2 robot development.
- Phase 2: AI Agent development, after `S1-2-G1` only.
- No AI model integration, AI Agent implementation, or physical robot operation is included in the current learning stage.

## Prerequisites

- Ubuntu 22.04
- ROS 2 Humble
- `colcon`
- Gazebo Classic and RViz2 for simulation verification

## Workspace Layout

```text
src/        ROS 2 packages
config/     runtime configuration
learning/   versioned learning materials
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
