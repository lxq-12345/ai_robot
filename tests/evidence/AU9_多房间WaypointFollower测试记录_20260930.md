# AU9 多房间 Waypoint Follower 测试记录

- 测试编号：AU9 多房间顺序导航（补充集成场景）
- 关联里程碑：S1-1-G1 / AU9
- 测试类型：自动
- Git提交：`109c8cd`（执行时工作区有未提交变更）
- 测试层级：集成
- 环境与依赖版本：ROS 2 Humble、Gazebo Classic、Nav2、AMCL；`apartment_v1.3.world`；默认GUI模式
- 自动测试前置条件及结果：先运行 `./scripts/start_au9_manual_nav2.sh`，确认Gazebo、地图、定位、Nav2和RViz2正常，`waypoint_follower`为Active；再在另一终端运行本测试客户端。测试脚本不启动或停止机器人环境。
- 执行命令：

  ```bash
  source /opt/ros/humble/setup.bash
  source install/setup.bash
  launch_test tests/integration/test_au9_waypoint_rooms.launch.py
  ```

- 输入与预期结果：通过单个 `/follow_waypoints` Action，按顺序访问主卧 `(4.70, 5.35, 90°)`、小孩房 `(5.20, 1.50, -90°)` 和起点 `(1.80, 4.00, 0°)`；预期Action成功、无遗漏航点、机器人有实际里程计位移，速度守卫限幅有效。
- 实际结果（拆分后的当前脚本）：`launch_test`退出码为0，`Ran 1 test in 278.887s — OK`。Waypoint Follower收到3个航点并报告 `Completed all 3 waypoints requested`；BT Navigator三次子目标均为 `Goal succeeded`，Action结果成功、遗漏航点为空且反馈索引包含0/1/2。实际路线三次出现 `Failed to make progress`，Nav2恢复后均继续成功；导航中也出现多次控制器“collision ahead”告警。人工Nav2环境仍保持运行，测试客户端已退出。
- 日志、截图、rosbag或报告路径：
  - 测试Launch：`/home/ubuntu/.ros/log/2026-09-30-02-11-47-199950-ubuntu-2629857/`
  - 手动Nav2 Launch：`/home/ubuntu/.ros/log/2026-09-30-02-10-30-995046-ubuntu-2623803/launch.log`
  - `/home/ubuntu/.ros/log/waypoint_follower_2624962_1790759442062.log`
  - `/home/ubuntu/.ros/log/bt_navigator_2624960_1790759442060.log`
  - `/home/ubuntu/.ros/log/controller_server_2624952_1790759442011.log`
- 操作者或执行主体：Codex；Gazebo仿真自动集成测试
- 结论：通过（多航点导航断言）；GUI清理存在异常
- 残留风险与后续动作：
  - 路线导航较慢，并出现三次进展失败及恢复；后续需结合门洞方向避障恢复变更复测。
  - 第一次以拆分后的脚本运行时，Launch过早结束并返回失败，尚未发送航点。增加仅维持测试Launch生命周期的420秒TimerAction后重跑通过；该Timer不启动机器人节点。
  - 更早的自启动版测试曾在RViz2清理时以退出码 `-11` 退出；本次外部手动环境保持运行，没有触发该清理路径。
  - 执行时工作区内的Nav2参数及行为树源码有未提交变更，且未执行构建；Launch通过安装空间加载 `ai_robot_sim`。因此本记录验证的是当前安装环境的Waypoint多房间流程，不代表源码中的新恢复行为已被构建或验证。
  - AU9-07 GUI人工体验仍未执行；本自动测试不替代人工观察证据。
- 当前测试脚本只连接外部运行中的 `/follow_waypoints` Action，不启动Gazebo/Nav2/RViz2；对应人工环境入口是 `./scripts/start_au9_manual_nav2.sh`。
- 环境预检自测（2026-09-30）：
  - 未启动主环境运行测试，12.335秒内以预期断言失败退出；提示缺少RViz2、AMCL、Map Server、BT Navigator、Waypoint Follower、`/follow_waypoints`及Gazebo `/clock`，并给出`./scripts/start_au9_manual_nav2.sh`启动建议。
  - 启动人工主环境后，首次预检因`/clock` QoS不兼容而误报缺失；将时钟订阅改为`qos_profile_sensor_data`后重跑，预检通过，三航点路线1项测试在257.594秒通过。
  - 正向运行日志位于`/home/ubuntu/.ros/log/2026-09-30-02-42-53-223978-ubuntu-2779244/`；手动环境Launch日志位于`/home/ubuntu/.ros/log/2026-09-30-02-41-11-481146-ubuntu-2771340/launch.log`。
  - 测试完成后向人工主Launch发送SIGINT，确认Gazebo、RViz2、AMCL、Nav2和关联Launch进程均已退出。
- 前述完整路线测试使用当时安装空间的Gazebo/Nav2资源和源码测试脚本，未验证方向性障碍恢复源码。后续逐段提示增强已由用户确认重跑通过。
- 逐段提示增强复测（2026-09-30）：用户确认更新后的Waypoint Follower逐段进度/结果提示代码已成功重跑验证。此次未提供运行日志、耗时或输出摘录；此记录不补写未提供的测试细节。此前完整路线测试结果仍见上文。
- L4正式测试尚未由学员执行，不得标记为通过或完成。
