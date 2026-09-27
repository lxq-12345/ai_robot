# AU8 Gazebo与RViz2协同

> 对应计划：AU8
> 教材版本：v1.4

## 1 学习目标

- 解释Gazebo、ROS 2节点和RViz2的完整数据闭环；
- 理解`/clock`、TF、Odometry、LaserScan、Image和CameraInfo；
- 能追踪一条数据如何从Gazebo/ROS 2到RViz2显示；
- 能定位Gazebo正常而RViz2异常、或反之的常见问题。

AU8先学习数据同步与观察链路，不要求本单元具备机器人运动、定位、导航或碰撞测试条件。

## 2 协同架构

核心链路为：

```text
Gazebo物理世界（`apartment_v1.3.world`）
  ├─ 底盘插件 → odom/TF
  ├─ 雷达插件 → /scan
  ├─ 小黄车左目 → /camera/image_raw + /camera/camera_info
  ├─ 小黄车右目 → /camera/right/image_raw + /camera/right/camera_info
  └─ IMU插件 → IMU消息
            ↓ ROS 2
SLAM / AMCL / Nav2 / robot_state_publisher
            ↓ Topic + TF
           RViz2
```

AU8只观察从Gazebo/ROS 2到RViz2的数据方向。RViz2目标交互、Nav2规划、安全速度链和Gazebo底盘执行属于AU9。

## 3 仿真时间

Gazebo发布`/clock`。使用仿真时间的节点必须配置`use_sim_time:=true`或由启动文件统一设置。时间配置不一致会造成消息过期、TF外推和超时判断异常。

暂停Gazebo后，仿真时间停止。此时基于仿真时间的节点可能看起来“卡住”，这是预期行为之一。

## 4 机器人模型与TF

`robot_state_publisher`读取`robot_description`和关节状态，发布机器人Link之间的TF。底盘或定位组件负责`odom`、`map`等全局链路。

典型链路：

```text
odom → base_footprint → base_link → laser_link
                                ├→ camera_link → camera_left_link → camera_left_optical_frame
                                │               └→ camera_right_link → camera_right_optical_frame
                                └→ imu_link
```

SLAM建图时`map→odom`通常由SLAM Toolbox发布；已有地图定位时由AMCL发布。二者不能同时争抢同一变换。

## 5 里程计与坐标链边界

底盘插件可以提供`odom→base_footprint`和里程计，`robot_state_publisher`发布`base_footprint→base_link`及传感器固定关系。AU8只检查这些接口、Frame和时间是否连通，不以车体位移或速度变化作为测试条件。

车体运动、里程计随动、导航目标与取消等动态验证统一放到AU9。直接用鼠标瞬移Gazebo模型不构成任何单元的正常运动证据。

## 6 雷达链路

Gazebo ray sensor生成LaserScan，ROS 2发布`/scan`，SLAM、AMCL和代价地图消费，RViz2显示。

雷达点与墙体不对齐可能来自：TF错误、时间戳问题、里程计漂移、定位错误、传感器安装位姿错误或地图不一致，不能只调地图分辨率。

## 7 相机链路

AU8使用小黄车v1.2的双目相机，不使用Nav2启动链默认加载的基础`ai_robot.urdf.xacro`。Gazebo左右相机模拟场景成像，插件发布图像和CameraInfo；RViz2的Image/Camera Display订阅数据并结合TF显示。

| 观察项 | 左目 | 右目 |
|---|---|---|
| Image | `/camera/image_raw` | `/camera/right/image_raw` |
| CameraInfo | `/camera/camera_info` | `/camera/right/camera_info` |
| Frame | `camera_left_optical_frame` | `camera_right_optical_frame` |
| 配置频率 | 10 Hz | 10 Hz |

验证时分别检查：

1. 图像Topic是否存在；
2. 发布频率是否接近配置值；
3. CameraInfo是否为640×480且内参字段有效；
4. 消息Frame是否为对应的`camera_*_optical_frame`，且能从`base_link`通过TF到达；
5. Gazebo光照、目标和相机朝向是否合理；
6. RViz2 Topic与QoS是否兼容。

## 8 地图与Gazebo世界

Gazebo World是三维物理真值环境；ROS地图是雷达和算法生成或加载的二维占用栅格。它们不是同一个文件，也不会自动保持绝对一致。

World中的墙通过雷达形成地图轮廓。仿真场景修改后，旧地图可能不再适用，需要重新建图或明确处理变化。

## 9 与AU9的边界

AU8到“Gazebo产生数据、ROS 2传递数据、RViz2正确显示”即结束。凡是需要设置目标、产生速度、驱动小车、观察路径或验证停车的内容，均在AU9学习和测试。

## 10 AU8专用启动与测试入口

AU8使用三个相互独立的入口，以支持Gazebo单独关闭和重启时保持RViz2运行。

终端A只启动Gazebo、房屋World和小黄车传感器：

```bash
cd /home/ubuntu/ai_robot_ws
./scripts/start_au8_gazebo.sh
```

终端B只启动RViz2：

```bash
cd /home/ubuntu/ai_robot_ws
./scripts/start_au8_rviz2.sh
```

终端C在两个GUI启动后检查数据链，执行完即退出：

```bash
cd /home/ubuntu/ai_robot_ws
./scripts/check_au8_gazebo_rviz2_sync.sh
```

三个入口固定组合：

- `apartment_v1.3.world`；
- `small_yellow_car_v1.2.sdf`及其左右相机插件；
- `small_yellow_car.rviz`；
- `use_sim_time:=true`；
- 左右Image、CameraInfo、发布频率、光学Frame、TF和QoS证据检查。

检查脚本的自动`PASS`证明数据链前置存在。画面内容、方向、光照、暂停/恢复、Gazebo单独关闭/重启和RViz2 Display状态可按`tests/scenario/AU8_Gazebo_RViz2协同测试.md`观察；个人截图与手工记录不作为本次AU8收尾的必要条件。

`ros2 launch ai_robot_sim nav2_bringup.launch.py gui:=true`不是AU8测试入口：它默认加载基础`ai_robot.urdf.xacro`，而非小黄车v1.2；且`rviz` 默认为`false`，不会建立本章要求的双界面双目观察基线。

## 11 教师引导操作

1. 在干净图形桌面中分别启动Gazebo和RViz2脚本；
2. 运行检查脚本，确认相机Topic、CameraInfo、TF、频率、RViz2仿真时间与订阅全部显示`PASS`；
3. 在Gazebo和RViz2中找到同一机器人；
4. 对照Gazebo视角、RViz2 RobotModel、TF和LaserScan（不发送运动命令）；
5. 把彩色目标放到相机前方，观察图像变化；
6. 暂停Gazebo，观察`/clock`、图像和雷达更新；
7. 恢复并记录同步恢复情况；
8. 单独关闭Gazebo但保持RViz2运行，记录各Display失联状态；
9. 单独重启Gazebo，观察RViz2自动恢复，再次运行检查脚本。

## 12 学员独立练习

建议完成一次“加载—观察墙体—观察相机目标—暂停—恢复”协同实验，并为每一步指出数据来源、ROS接口和RViz2显示项。小车运动和导航归AU9，障碍与碰撞综合观察归AU10。

## 13 正常现象

- Gazebo与RViz2中的机器人模型、TF和传感器Frame关系一致；
- 雷达点随姿态和环境变化；
- 相机画面随目标和朝向变化；
- 暂停仿真后基于仿真时间的数据停止更新；
- 恢复后链路继续工作；
- 地图中的墙与雷达点大致对齐。

## 14 常见问题定位顺序

1. Gazebo模型和传感器是否运行；
2. `/clock`是否更新；
3. Topic是否存在且有新消息；
4. 消息Frame和时间戳是否正确；
5. TF链是否连通；
6. 算法节点是否Active；
7. RViz2 Fixed Frame、Topic和QoS是否正确；
8. 显示属性是否把数据隐藏。

## 15 理解检查

1. Gazebo World和ROS Map为什么不是同一个对象？
2. 鼠标瞬移为什么会破坏协同判断？
3. `/clock`停止会影响哪些现象？
4. 相机黑屏时为什么不能只查RViz2？
5. SLAM和AMCL为什么不能同时发布`map→odom`？

## 16 技能检查与证据

能从Gazebo/RViz2现象追踪到Topic、TF和数据发布组件，且项目技术检查证明双目图像、CameraInfo、Frame、TF、仿真时间、RViz2订阅与重启恢复正常，即可形成AU8结论。个人截图与手工记录可选；运动、导航和碰撞结果不属于AU8完成条件。

## 17 项目内依据

- `scripts/start_au8_gazebo.sh`
- `scripts/start_au8_rviz2.sh`
- `scripts/check_au8_gazebo_rviz2_sync.sh`
- `tests/scenario/AU8_Gazebo_RViz2协同测试.md`
- `ai_robot_sim/launch/apartment_house_bringup.launch.py`
- `ai_robot_description/models/small_yellow_car_v1.2.sdf`
- `config/rviz2/small_yellow_car.rviz`
