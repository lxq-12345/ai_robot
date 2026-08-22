# S1-1-M5-L1-01 SLAM建图与地图管理

> 所属开发单元：S1-1-M5 SLAM、定位与Nav2<br>
> 所属学习子单元：S1-1-M5-L1 SLAM建图与地图管理<br>
> 章节序号：S1-1-M5-L1-01<br>
> 教材版本：v1.0<br>
> 涉及组件：`ai_robot_sim`、SLAM Toolbox、Nav2 Map Saver<br>
> 安全边界：仅在Gazebo中建图；运动使用项目受控入口，不直接发布速度Topic。

[TOC]

## 1. 学习目标

理解激光扫描、里程计和TF如何进入SLAM Toolbox，`/map`与`map -> odom`如何形成，以及地图如何保存为YAML和图像并供后续定位重载。建图是数据与位姿的联合估计，不是简单截图。

## 2. 建图链路

```text
/scan（laser_link）
+ odom -> base_link
+ base_link -> laser_link
→ slam_toolbox
→ /map
→ map -> odom
→ map_saver_server
→ YAML + PGM
```

`config/slam_sim.yaml`设置`map/odom/base_link`、`/scan`、0.05 m分辨率、运动更新阈值和8 m最大雷达范围。`slam_bringup.launch.py`组合基础仿真、SLAM节点、地图保存服务和生命周期管理器。

## 3. 地图资源

地图YAML描述图像文件、分辨率、原点、占用与空闲阈值；PGM保存栅格。两者必须配套，路径和元数据必须可重载。临时测试地图写入测试目录或`/tmp`，正式基准地图才进入包资源。

## 4. 自动测试阅读与复现

`tests/integration/test_s1_m5_slam.launch.py`验证：

- `/map`发布且Frame为`map`；
- 栅格尺寸有效；
- SLAM发布`map -> odom`；
- 保存服务成功；
- YAML和PGM实际生成。

```bash
cd /home/ubuntu/ai_robot_ws
./scripts/build.sh
source install/setup.bash
launch_test tests/integration/test_s1_m5_slam.launch.py
```

## 5. 人工练习与正常现象

启动`ros2 launch ai_robot_sim slam_bringup.launch.py`，在RViz2以`map`为Fixed Frame观察LaserScan、Map、RobotModel和TF。使用受控运动覆盖可见区域，观察地图逐步扩展；通过地图保存服务保存练习地图并检查YAML/PGM。

正常现象是地图随探索增长，机器人轨迹与墙体一致，TF链`map -> odom -> base_link -> laser_link`连续，保存文件可读。严重重影、跳变或地图不增长均不能记录通过。

## 6. 常见问题与停止

- 无`/map`：查生命周期、扫描和TF；
- 地图不更新：查仿真是否移动、更新阈值和时间；
- 重影：查里程计、TF、扫描时间和运动过快；
- 保存失败：查服务状态、目录权限和地图是否有效；
- 重载偏移：查YAML原点、分辨率和图像路径。

停止前让受控运动归零，再按`Ctrl+C`退出SLAM和Gazebo。证据保留地图截图、文件摘要、TF观察和日志。

## 7. 实体迁移与证据

实体阶段保留`/scan`、TF、`/map`和保存接口，但必须重做雷达安装标定、里程计参数、时间同步、运动速度和现场地图。证据记录测试命令、地图文件、人工探索、异常和结论。

## 8. 理解检查

1. SLAM为什么同时需要扫描和里程计/TF？
2. 谁发布`map -> odom`？
3. YAML与PGM分别保存什么？
4. 地图重影时为什么不能只调分辨率？
5. 仿真地图能否直接作为实体地图？

## 9. 项目内依据

- `src/ai_robot_sim/launch/slam_bringup.launch.py`
- `config/slam_sim.yaml`
- `tests/integration/test_s1_m5_slam.launch.py`
- `tests/README.md`

