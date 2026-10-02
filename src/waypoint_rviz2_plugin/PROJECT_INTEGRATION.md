# 项目集成记录

来源：https://github.com/castacks/3d-waypoint-rviz2-plugin
上游基线：dee0cbca4e82d368975a19c276ed632be267c818
包版本：1.0.0；package.xml声明许可证Apache-2.0。
环境：Ubuntu 22.04、ROS 2 Humble。

本工作空间以普通源码文件保存此插件；本地嵌套.git不纳入父仓库，也不使用仅保存引用的gitlink。
项目改动包括独立/waypoint_path Topic、InteractiveMarkers订阅命名空间适配、浅蓝半透明圆环及航点坐标轴缩短。
最终模型节点scale=0.04；InteractiveMarker.scale=0.2；圆环生成时scale=1.0。
构建：colcon build --packages-select waypoint_rviz2_plugin --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3。
依据：tests/evidence/AU9_Waypoint交互轴比例验证_20261002.md；用户于2026-10-02确认Waypoint坐标通过。
本次只验收坐标轴显示，完整拖拽/旋转回归及AU9/Gate不由此完成。
