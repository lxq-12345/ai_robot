# S1-1-M3传感器GUI观察说明

## 目标

在Gazebo Classic GUI中人工观察S1-1-M3仿真传感器模型、机器人本体和传感器数据链路。该观察仅用于仿真验证，不涉及实体机器人上电、运动或硬件测试。

## 前置条件

- 已执行`./scripts/build.sh`。
- 当前Shell已加载工作空间环境。
- ToDesk或本地桌面可显示X11窗口。

## 启动命令

终端1：

```bash
source install/setup.bash
ros2 launch ai_robot_sim sim_bringup.launch.py gui:=true
```

终端2可观察Topic：

```bash
source install/setup.bash
ros2 topic hz /scan
ros2 topic hz /camera/image_raw
ros2 topic hz /imu/data
ros2 topic echo --once /camera/camera_info
ros2 topic echo --once /joint_states
```

终端3可执行M2底盘演示，辅助观察编码器与IMU变化：

```bash
source install/setup.bash
ros2 run ai_robot_sim manual_motion_demo
```

## 观察点

- Gazebo中可见机器人底盘、左右轮、雷达、相机和IMU安装位置。
- `/scan`持续发布，`header.frame_id`为`laser_link`。
- `/camera/image_raw`持续发布，`header.frame_id`为`camera_link`，分辨率为640x480。
- `/camera/camera_info`持续发布，frame与图像一致。
- `/imu/data`持续发布，`header.frame_id`为`imu_link`。
- `/joint_states`包含`left_wheel_joint`和`right_wheel_joint`。

## 通过标准

- 所有传感器Topic可被ROS 2 CLI观察到。
- 传感器frame与`config/sim_sensors.yaml`一致。
- 执行`manual_motion_demo`时，`/joint_states`左右轮速度发生变化。
- 不直接发布`/cmd_vel`，底盘演示仍通过`/cmd_vel_raw -> cmd_vel_guard -> /cmd_vel`链路。
