# S1-1-M5-L4 Gazebo/RViz2 GUI人工体验执行清单

> 关联主线：`S1-1-M5-L4 建图、定位与导航测试及证据`  
> 关联辅助课程：`learning/Gazebo与RViz2辅助/`中的AU8、AU9、AU10  
> 目的：补齐M5-L4遗留的GUI人工体验、截图/观察记录和证据结论。  
> 边界：仅限Gazebo仿真；不执行实体机器人操作；不绕过`cmd_vel_guard`。

## 1. 执行前记录

- 日期与操作者；
- Git提交号或项目版本；
- Ubuntu、ROS 2、Gazebo Classic、RViz2版本；
- 使用的World、地图、RViz2配置和Launch命令；
- 构建命令与结果；
- 上一轮Gazebo、RViz2、SLAM、AMCL、Nav2和ROS节点是否已清理。

## 2. 启动与显示

1. 启动Gazebo GUI和M5所需SLAM或定位/Nav2链路；
2. 启动RViz2，使用已有配置或按AU7手工添加核心Display；
3. 确认Fixed Frame为`map`；
4. 确认Map、LaserScan、RobotModel、TF、Path、Odometry、Image或Camera显示状态可解释；
5. 截图保存Gazebo全景和RViz2主视图。

## 3. 定位或建图观察

- 若使用SLAM：观察`/map`增长、`map -> odom`存在、雷达与墙体轮廓基本一致；
- 若使用已有地图定位：设置初始位姿，观察AMCL粒子收敛、雷达与地图墙体基本对齐；
- 确认项目当前TF链为`map -> odom -> base_footprint -> base_link -> sensor_link`。

## 4. 可达目标导航

1. 在RViz2设置一个可达目标；
2. 观察目标是否被Nav2接受；
3. 观察全局路径、局部控制、Gazebo小车运动和RViz2 RobotModel同步；
4. 观察速度命令仍经过项目安全链；
5. 记录Action状态、路径截图和到点结论。

## 5. 导航取消与停车

1. 再设置一个可达目标；
2. 小车运动中执行取消；
3. 记录Action最终状态；
4. 同时观察安全速度回零、里程计变化停止和Gazebo小车停车；
5. 取消成功但小车仍滑行时，结论不能写通过，需记录异常层级。

## 6. 临时障碍观察

1. 在原本可通行路线放置临时障碍；
2. 观察Gazebo障碍物位置；
3. 观察LaserScan和局部代价地图变化；
4. 记录Nav2减速、停车或绕行；
5. 移除障碍并观察代价地图清除和路线恢复。

## 7. 安全停车观察

按项目允许的已有测试或人工入口观察扫描超时安全停车现象。证据应记录原始速度、安全速度、扫描新鲜度、Gazebo小车运动和最终结论。

## 8. 证据模板

```text
练习名称：
项目版本：
环境：
使用文件：
启动命令：
人工操作：
预期现象：
实际现象：
Action/节点状态：
截图/日志：
进程清理：
结论：通过 / 失败 / 未执行
问题与备注：
```

建议证据文件：

```text
tests/evidence/S1-1-M5-L4_Gazebo_RViz2_GUI人工体验记录_YYYYMMDD.md
```

## 9. 完成条件

- 目标取消、可达目标、路径、速度和停车均已人工观察；
- Gazebo与RViz2截图齐全；
- Action状态、TF、地图或定位、障碍响应和安全停车记录可追溯；
- 结束后无未解释残留进程；
- 结论明确写为通过、失败或未执行。
