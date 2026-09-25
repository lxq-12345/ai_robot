# AU8 Gazebo与RViz2协同测试记录

- 时间：2026-09-25
- 环境：ROS 2 Humble、Gazebo Classic、RViz2
- 场景：`apartment_v1.3.world`、`small_yellow_car_v1.2.sdf`
- 执行主体：Codex在用户连续执行授权下完成技术验证
- 安全边界：仅仿真；未发布速度、导航或实体设备控制命令

## 入口

```bash
./scripts/start_au8_gazebo.sh
./scripts/start_au8_rviz2.sh
./scripts/check_au8_gazebo_rviz2_sync.sh
```

Gazebo、RViz2和检查器分别由独立入口启动，检查器不拥有也不清理两个GUI进程。

## 修正前问题与定位

- 单实例检查曾测得左目ROS 2接收频率约6.45 Hz，低于7 Hz验收下限。
- Gazebo性能指标中双目`real_update_rate`、`sim_update_rate`和FPS均约10，Gazebo原生左右图像Topic也约10 Hz，排除插件频率配置与成像故障。
- RViz2旧配置对左图像存在Camera和Image两个可靠订阅；旧实例日志同时记录`queue is full`丢帧。
- 配置改为Camera Left订阅`/camera/image_raw`、Image Right订阅`/camera/right/image_raw`，每路各一个图像订阅，保留Image/Camera两类Display学习目标。

## 第一次完整检查

- 左右图像Publisher各1个，RViz2 Subscription各1个。
- `/camera/image_raw`：7.972 Hz，通过。
- `/camera/right/image_raw`：8.316 Hz，通过。
- 左右Image、CameraInfo、光学Frame、TF、RViz2仿真时间、订阅与QoS检查全部通过。
- QoS日志：`log/manual/au8_camera_qos_20260925_054305.log`。

## Gazebo独立停止与恢复

1. 仅停止Gazebo入口，确认`gzserver`和`gzclient`全部退出。
2. RViz2保持运行，`use_sim_time=True`。
3. 失联期间左右图像与雷达Topic均为Publisher 0、RViz2 Subscription 1。
4. 仅重新启动Gazebo，双目Topic恢复，RViz2全程未重启。

## 恢复后第二次完整检查

- `/camera/image_raw`：8.683 Hz，通过。
- `/camera/right/image_raw`：8.623 Hz，通过。
- 左右Image、CameraInfo、光学Frame、TF、RViz2仿真时间、订阅与QoS检查全部通过。
- QoS日志：`log/manual/au8_camera_qos_20260925_054502.log`。
- 重启Gazebo日志：`log/manual/au8_gazebo_20260925_054426.log`。

## GUI观察证据

- `tests/evidence/AU8_Gazebo_20260925.png`：房屋场景光照正常，黄色小车位于室内，Gazebo显示实时因子1.00。
- `tests/evidence/AU8_RViz2_20260925.png`：`Global Status: Ok`，Camera Left和Image Right均有房屋前方场景画面，RobotModel、TF和LaserScan可见。

## 静态验证与清理

- `/usr/bin/python3 -m pytest src/ai_robot_sim/test/test_sim_entrypoints.py -q`：`10 passed in 0.04s`。
- `git diff --check`：通过。
- 测试结束后无Gazebo、RViz2、相关ROS节点或11345端口残留，ROS 2 daemon已停止。

## 结论

AU8三个独立入口、Gazebo与RViz2协同数据链、Gazebo单独停止/重启和RViz2自动恢复的技术验证通过。本记录不代替学员对Topic、TF、CameraInfo、QoS和仿真时间的个人理解检查。
