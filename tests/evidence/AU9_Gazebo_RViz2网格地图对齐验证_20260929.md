# AU9 Gazebo/RViz2网格地图对齐验证

- 时间：2026-09-29 02:59 PDT
- 范围：Gazebo Classic房屋可见地面、Gazebo参考Grid、RViz2参考Grid与Nav2占用栅格地图。
- 操作人结论：人工检查通过。
- 安全边界：仅限仿真；本轮未发送导航目标或速度命令。

## 问题与修正

- 原Gazebo可见地面范围为`X=-3.00..9.19`、`Y=-3.00..10.48`，与Nav2地图`X=-0.50..6.70`、`Y=-0.50..8.00`不一致。
- Gazebo Classic SDF 1.6的`scene/grid`只提供显示开关，不提供网格尺寸或Offset配置；因此修正Gazebo可见地面，不移动房屋或导航坐标。
- `floor_visual`调整为`7.20 m × 8.50 m`，世界中心为`(3.10,3.75)`，因而边界与Nav2地图完全相同。
- 可见地面顶面略低于`Z=0`，使Gazebo参考Grid可见。
- Gazebo物理碰撞地面仍保持`12.19 m × 13.48 m`，不改变小车物理运动范围。
- RViz2 Grid使用`map`坐标系，Offset为`(0,0,-0.01)`；仅TopDownOrtho相机以`(3.10,3.75)`居中。

## 验证

- `gz sdf -k src/ai_robot_sim/worlds/apartment_v1.3.world`：`Check complete`。
- `/usr/bin/python3 -m pytest src/ai_robot_sim/test/test_sim_entrypoints.py -q`：`13 passed in 0.05s`。
- `colcon build --packages-select ai_robot_sim --symlink-install`：通过。
- 运行时Gazebo加载安装后`apartment_v1.3.world`，RViz2加载安装后`au9_nav2.rviz`，AMCL与Nav2正常Active。
- 操作人对Gazebo/RViz2中网格与地图的相对位置进行人工检查，结论为“通过”。
- `Ctrl+C`收尾后无相关进程、ROS 2节点或`11345`端口残留，daemon已停止。

## 剩余边界

- RViz2在SIGINT收尾时仍返回既有`-11`，本轮GUI运行和观察正常。
- 本记录只完成网格—地图对齐观察；AU9-07小车人工Nav2目标移动、路径、到点停车与取消停车结论仍待完成。
