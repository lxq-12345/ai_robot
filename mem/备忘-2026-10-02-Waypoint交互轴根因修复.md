# Waypoint交互坐标轴根因修复

时间：2026-10-02 02:22 PDT
阶段：阶段1——AU9；实体未授权。
目标：将当前可见航点坐标轴缩短五倍。
耗时：未统计。

- 用户授权自主决定并继续修改，保留生成模型0.04并统一预览0.04。
- 首轮构建后真实GUI仍显示约80像素轴，证明单改Ogre模型缩放无效；该失败没有被当作通过。
- 根因：InteractiveMarker.scale仍为1.0，RViz生成的轴不受Ogre mesh节点缩放控制。
- 修复：InteractiveMarker.scale改为0.2；makeDisc时临时使用1.0再恢复0.2，保留圆环生成尺寸。
- waypoint_rviz2_plugin第二轮定向构建退出码0；diff检查通过。
- ROS_DOMAIN_ID=87隔离RViz实际生成两个航点，同TopDownOrtho Scale=80下轴长约16像素，原截图约80像素。新截图暗红轴连续像素为15（端点/抗锯齿影响），验证可见长度约五分之一。
- 初次像素检测阈值过高，未匹配暗红轴；调整颜色检测阈值后得到上述列计数，未修改产品代码。
- 新截图：tests/evidence/AU9_Waypoint交互坐标轴修复_20261002.png。
- 测试会话SIGINT退出码0，未启动Gazebo/Nav2，未发送运动指令。
- 用户原RViz与未保存航点未关闭；其插件仍为旧加载实例，重新启动前不会自动更新。
- 修改文件：src/waypoint_rviz2_plugin/src/waypoint_tool.cpp、证据、状态及索引。
- 此前仅模型缩放的比例通过结论已撤回，以本次交互轴对照结果为准。
- 技术工作完成，远端归档未完成；下一步用户保存航点并重新加载RViz，随后定向归档。本次不完成AU9整体或Gate。
