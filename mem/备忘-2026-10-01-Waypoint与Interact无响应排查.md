# 阶段备忘

备忘时间：2026-10-01 04:36 PDT  
备忘主题：RViz2 Interact无法操作WaypointTool航点的原因定位  
关联阶段：阶段 1——S1-1-G1前置；Gazebo/RViz2辅助课程AU9  
开发环境：Ubuntu GNOME、ROS 2 Humble、RViz2、WaypointTool插件  
当前唯一执行目标：定位RViz2 Interact未能选中或拖动WaypointTool航点的原因  
实体设备操作授权：未授权（本次只读检查）  
开始时间：未统计  
结束时间：2026-10-01 04:36 PDT  
实际耗时：未统计

## 本阶段完成内容

- 检查`waypoint_rviz2_plugin`源码：WaypointTool通过`InteractiveMarkerServer("waypoint_plugin")`为新航点注册交互标记，同时另用Ogre SceneNode绘制可见坐标轴模型。
- 当前AU9 RViz配置没有`rviz_default_plugins/InteractiveMarkers`显示。Interact工具不能直接选中插件单独绘制的Ogre SceneNode；必须有InteractiveMarkers显示订阅交互标记更新，才能渲染和接收交互控制。
- 运行态ROS图确认`/waypoint_plugin/update`类型为`visualization_msgs/msg/InteractiveMarkerUpdate`，有1个RViz发布者、0个订阅者；`/waypoint_plugin/feedback`话题存在。
- 已安装的RViz默认插件清单确认存在`rviz_default_plugins/InteractiveMarkers`，消息类型为`visualization_msgs/msg/InteractiveMarkerUpdate`。
- 插件README也要求添加该InteractiveMarkers显示；配置缺项导致用户选中Interact后航点无响应。

## 修改的文件

- 无代码、配置或测试修改。本备忘记录只读检查结果。
- `mem/当前状态.md`、`mem/备忘索引.md`：同步当前排查结论。

## 构建、测试与运行结果

- 只读命令`ros2 topic list -t`：看到`/waypoint_plugin/update`和`/waypoint_plugin/feedback`。
- `ros2 topic info /waypoint_plugin/update -v`：1个发布者、0个订阅者。
- 未构建、未运行测试、未重启仿真。

## 关键决策与安全影响

- Interact是RViz操作工具；InteractiveMarkers是承载交互标记的RViz Display，两者作用不同。启用Interact本身不会为Marker Server创建显示订阅。
- 后续若修复，应在AU9 RViz配置中加入`rviz_default_plugins/InteractiveMarkers`显示并将其Topic设为`/waypoint_plugin/update`，随后重启RViz并验证选中、拖动与反馈同步。此次用户仅要求检查，未做该配置改动。

## 残留风险

- 尚未实测添加InteractiveMarkers显示后的鼠标选中、拖动和WayPointTool面板坐标同步行为。

## 下一步

1. 按用户后续指示将InteractiveMarkers Display加入AU9配置，并验证完整交互链路。
