# rosbag 记录与回放模板

## 记录元数据

- 记录编号：
- 日期与操作者：
- 关联阶段与测试编号：
- 仿真或实体环境：
- Git提交：
- ROS 2发行版：
- 地图、世界与参数版本：
- 启动命令：

## 录制范围

| Topic | 消息类型 | 录制原因 | QoS覆盖 |
|---|---|---|---|
| /tf | tf2_msgs/msg/TFMessage | 坐标变换证据 | 否 |
| /tf_static | tf2_msgs/msg/TFMessage | 静态坐标变换证据 | 否 |
| /odom | nav_msgs/msg/Odometry | 底盘与定位证据 | 否 |
| /scan | sensor_msgs/msg/LaserScan | 雷达链路证据 | 否 |
| /diagnostics | diagnostic_msgs/msg/DiagnosticArray | 健康状态证据 | 否 |

## 命令模板

```bash
ros2 bag record -o resources/rosbag/{record_id} /tf /tf_static /odom /scan /diagnostics
ros2 bag info resources/rosbag/{record_id}
ros2 bag play resources/rosbag/{record_id}
```

## 回放验收

- [ ] `ros2 bag info`可读取元数据和Topic清单。
- [ ] 回放时钟、TF和消息时间戳可观察。
- [ ] 契约检查在回放数据上可重复执行。
- [ ] 原始录包路径、日志和结果已链接到测试证据。
