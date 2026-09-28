# AU9 导航操作与路径工具测试

> 范围：仅限Gazebo仿真；复用AU8的`apartment_v1.3.world`、`small_yellow_car_v1.2.sdf`及其专用占用栅格地图。
> 安全：速度必须经`/cmd_vel_raw -> cmd_vel_guard -> /cmd_vel`；不直接发布两个速度Topic，不操作实体机器人。

## 1. 测试目标

验证AU9中的定位前置、单目标导航、多航点、运动中取消、安全停车、速度限幅和Gazebo/里程计反馈。

## 2. 案例矩阵

| 编号 | 案例 | 操作 | 通过标准 |
|---|---|---|---|
| AU9-01 | 定位与生命周期 | 启动稳定世界、AMCL和Nav2，发布初始位姿 | `map -> odom`存在，BT Navigator和Waypoint Follower为Active |
| AU9-02 | 多航点 | 小黄车从`(1.80, 4.00)`出发，通过`FollowWaypoints`依次访问`(1.50, 4.00)`和`(1.20, 4.00)` | Action为`SUCCEEDED`，无遗漏航点，里程计位移大于0.35 m |
| AU9-03 | 运动中取消 | 向`(1.80, 5.80)`发送单目标，确认已运动后取消 | 取消被接受，Action最终为`CANCELED` |
| AU9-04 | 取消后停车 | 取消后继续观察安全速度 | 0.5 s宽限后不再出现非零安全速度 |
| AU9-05 | 单目标导航 | 从取消点导航回`(1.80, 4.00)` | Action为`SUCCEEDED` |
| AU9-06 | 安全速度链 | 观察`/cmd_vel_raw`与`/cmd_vel` | 两端均有运动命令；安全线速度不超0.35 m/s，角速度不超1.20 rad/s |
| AU9-07 | GUI协同观察 | 在Gazebo和RViz2观察目标、路径、小车、雷达、代价地图 | 两个GUI与Action、TF、里程计现象一致 |

## 3. 自动实测

在干净环境执行：

```bash
cd /home/ubuntu/ai_robot_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
launch_test tests/integration/test_au9_navigation_tools.launch.py
```

该入口执行AU9-01至AU9-06，使用真实Gazebo、房屋地图、小黄车、AMCL、Nav2、Waypoint Follower和项目安全守卫，不使用假Action Server。

## 4. GUI观察

终端A：

```bash
cd /home/ubuntu/ai_robot_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ai_robot_sim apartment_nav2_bringup.launch.py gui:=true rviz:=true
```

操作人在RViz2中设置安全目标并使用Nav2面板取消，同时观察Gazebo小黄车。房屋出生点为`(1.80, 4.00)`，不应使用旧M5世界的目标坐标。

AI执行只记为技术实测；AU9-07的学员GUI个人证据仍需由学员操作和确认。

## 5. 失败与清理

- 任一案例失败时立即停止，保留首个失败和日志，不用后续结果覆盖。
- 先按`Ctrl+C`停止测试和Launch，再确认Gazebo、Nav2、RViz2与ROS 2节点无残留。
- 仅对明确的残留进程执行定向清理，不使用宽泛的`killall`或`pkill -9`。

## 6. 证据

记录Git提交、命令、每个案例结果、Action状态、里程计位移、速度限幅、GUI截图/观察、清理结果和最终结论。只有AU9-01至AU9-07均通过才可将AU9标记完成。
