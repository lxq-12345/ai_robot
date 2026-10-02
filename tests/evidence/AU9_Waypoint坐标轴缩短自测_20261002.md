# Waypoint坐标轴缩短自测

时间：2026-10-02 02:13 PDT
操作者：Codex自动GUI操作；不是学员人工学习证据。

- 修改：预览与生成航点Ogre节点均等比缩放0.2，轴长度为原来的五分之一，粗细同步缩小。
- 构建：waypoint_rviz2_plugin定向构建成功，安装动态库存在；源码定向断言和diff检查通过。
- 运行：ROS_DOMAIN_ID=87，使用log/waypoint_axis_check/check.rviz临时配置；只保留Grid及InteractiveMarkers，Fixed Frame为map，不启动Gazebo或Nav2。
- 操作：通过XTest点击Waypoint Tool，再点击视口生成航点；Total waypoints显示1，Selected wp为point#1，坐标约X=3.57、Y=3.92、Z=0。
- 观察：生成航点红绿坐标轴正常渲染，轴线各约80屏幕像素；视图Scale=80，结合源节点缩放0.2确认缩短设置已用于运行产物。未做旧版本截图对比。
- 截图：AU9_Waypoint坐标轴五分之一_20261002.png，仅包含测试RViz窗口。
- 日志：log/waypoint_axis_check/rviz.log未匹配error/failed；安装产物启动与生成航点成功。
- 清理：核对测试RViz命令行后发送SIGINT，启动会话退出码0；未发送导航、速度或实体控制命令。
- 结论：本次坐标轴缩短功能GUI自测通过。拖拽/旋转完整回归不在本次结论范围；既有停止修复、AU9整体和Gate不由本证据完成。
