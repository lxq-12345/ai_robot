# AU8 Gazebo与RViz2协同测试

## 1. 目的与边界

本场景使用房屋World、小黄车v1.2双目相机和项目RViz2配置，验证Gazebo、ROS 2与RViz2之间的仿真时间、TF、雷达和相机数据链。场景不发送运动或导航命令，仅限仿真。

## 2. 独立启动命令

打开三个Ubuntu图形桌面终端。

终端A只启动Gazebo：

```bash
cd /home/ubuntu/ai_robot_ws
./scripts/start_au8_gazebo.sh
```

终端B只启动RViz2：

```bash
cd /home/ubuntu/ai_robot_ws
./scripts/start_au8_rviz2.sh
```

终端C在两个GUI都就绪后执行数据链检查：

```bash
cd /home/ubuntu/ai_robot_ws
./scripts/check_au8_gazebo_rviz2_sync.sh
```

三个脚本互不拥有对方的进程。停止终端A的Gazebo不会关闭终端B的RViz2；重新执行终端A命令即可单独恢复Gazebo。

## 3. 自动检查

- Gazebo入口启动`apartment_v1.3.world`和`small_yellow_car_v1.2.sdf`；
- 确认`/clock`、`/scan`、左右图像和左右CameraInfo Topic存在；
- 确认左右图像与CameraInfo分别使用`camera_left_optical_frame`和`camera_right_optical_frame`；
- 确认两个光学Frame可从`base_link`通过TF到达；
- 确认CameraInfo分辨率为640×480；
- 确认左右图像实测频率处于7至13 Hz；
- RViz2入口独立启动`small_yellow_car.rviz`并启用仿真时间；
- RViz2以Camera Left显示左目、Image Right显示右目，避免同一图像Topic被重复订阅；
- 保存Gazebo、RViz2和相机QoS本地日志。

自动检查只证明接口和运行条件存在，不能替代GUI人工观察。

## 4. 人工观察

1. 在Gazebo确认黄色小车、房屋光照和相机前方目标合理；
2. 在RViz2确认Camera Left和Image Right均有画面；
3. 确认画面内容与Gazebo中小车朝向及前方场景一致；
4. 查看Image/Camera Display状态，解释Topic、CameraInfo、TF和QoS；
5. 在Gazebo中点击暂停，确认`/clock`、图像和雷达停止更新，再恢复仿真并确认显示恢复；
6. 在终端A按`Ctrl+C`单独关闭Gazebo，保持RViz2运行，记录Image、Camera、LaserScan和TF的失联状态；
7. 在终端A重新执行Gazebo启动命令，观察RViz2数据和Display状态自动恢复；
8. 再次执行终端C检查，确认重启后的Topic、TF、频率、订阅和QoS证据通过；
9. 保存Gazebo与RViz2截图、两次PASS输出和日志路径。

## 5. 停止与证据

终端A的`Ctrl+C`只停止Gazebo，终端B的`Ctrl+C`只停止RViz2；终端C检查脚本执行完后自行退出，不启动也不停止GUI。不得使用广域`killall`。

证据至少记录：命令、项目版本、自动检查结果、实际画面、暂停/恢复现象、截图/日志、进程清理和明确结论。建议保存为：

```text
tests/evidence/AU8_Gazebo_RViz2协同测试记录_YYYYMMDD.md
```
