# AU8 Gazebo与RViz2协同

> 对应计划：AU8
> 教材版本：v1.1

## 1 学习目标

- 解释Gazebo、ROS 2节点和RViz2的完整数据闭环；
- 理解`/clock`、TF、Odometry、LaserScan、Image和CameraInfo；
- 能追踪一条数据如何从Gazebo/ROS 2到RViz2显示；
- 能定位Gazebo正常而RViz2异常、或反之的常见问题。

AU8先学习数据同步与观察链路，不要求本单元具备机器人运动、定位、导航或碰撞测试条件。

## 2 协同架构

核心链路为：

```text
Gazebo物理世界
  ├─ 底盘插件 → odom/TF
  ├─ 雷达插件 → /scan
  ├─ 相机插件 → /camera/image_raw + /camera/camera_info
  └─ IMU插件 → IMU消息
            ↓ ROS 2
SLAM / AMCL / Nav2 / robot_state_publisher
            ↓ Topic + TF
           RViz2
```

控制方向相反：在后续导航单元中，RViz2可发送目标，Nav2规划和控制，速度命令经过项目安全链后驱动Gazebo底盘；AU8只解释该链路，不执行导航目标。

## 3 仿真时间

Gazebo发布`/clock`。使用仿真时间的节点必须配置`use_sim_time:=true`或由启动文件统一设置。时间配置不一致会造成消息过期、TF外推和超时判断异常。

暂停Gazebo后，仿真时间停止。此时基于仿真时间的节点可能看起来“卡住”，这是预期行为之一。

## 4 机器人模型与TF

`robot_state_publisher`读取`robot_description`和关节状态，发布机器人Link之间的TF。底盘或定位组件负责`odom`、`map`等全局链路。

典型链路：

```text
map → odom → base_footprint → base_link → laser_link
                                      ├→ camera_link
                                      └→ imu_link
```

SLAM建图时`map→odom`通常由SLAM Toolbox发布；已有地图定位时由AMCL发布。二者不能同时争抢同一变换。

## 5 里程计与运动数据（概念观察）

小车在Gazebo中通过控制链运动时，底盘插件产生`odom→base_footprint`关系和里程计，`robot_state_publisher`继续发布`base_footprint→base_link`及传感器固定关系。AU8只分析已有消息或静态配置中的链路，不发送运动命令；RViz2根据TF更新机器人显示。

直接用鼠标瞬移Gazebo模型可能造成物理位姿、里程计和定位估计不一致，因此不能把瞬移当作正常协同测试。

## 6 雷达链路

Gazebo ray sensor生成LaserScan，ROS 2发布`/scan`，SLAM、AMCL和代价地图消费，RViz2显示。

雷达点与墙体不对齐可能来自：TF错误、时间戳问题、里程计漂移、定位错误、传感器安装位姿错误或地图不一致，不能只调地图分辨率。

## 7 相机链路

Gazebo相机模拟场景成像，插件发布图像和CameraInfo。RViz2的Image/Camera Display订阅数据并结合TF显示。

验证时分别检查：

1. 图像Topic是否存在；
2. 发布频率是否接近配置值；
3. CameraInfo是否有效；
4. Frame是否在TF树中；
5. Gazebo光照、目标和相机朝向是否合理；
6. RViz2 Topic与QoS是否兼容。

## 8 地图与Gazebo世界

Gazebo World是三维物理真值环境；ROS地图是雷达和算法生成或加载的二维占用栅格。它们不是同一个文件，也不会自动保持绝对一致。

World中的墙通过雷达形成地图轮廓。仿真场景修改后，旧地图可能不再适用，需要重新建图或明确处理变化。

## 9 控制闭环（后续导航预览）

单目标导航示例（仅作后续课程预览，AU8不执行）：

1. 用户在RViz2点选目标；
2. RViz2发送NavigateToPose目标；
3. Nav2使用地图、代价地图、TF、里程计和雷达规划；
4. Nav2输出原始速度；
5. 项目安全守卫检查后发送安全速度；
6. Gazebo底盘执行；
7. 新的里程计和传感器数据反馈；
8. RViz2更新机器人、路径和代价地图。

## 10 教师引导操作

1. 启动可用的仿真与观察入口；若SLAM、定位或Nav2尚未具备，只记录为前置条件；
2. 启动项目RViz2配置；
3. 在Gazebo和RViz2中找到同一机器人；
4. 对照Gazebo视角、RViz2 RobotModel、TF和LaserScan（不发送运动命令）；
5. 把彩色目标放到相机前方，观察图像变化；
6. 暂停Gazebo，观察`/clock`、图像和雷达更新；
7. 恢复并记录同步恢复情况。

## 11 学员独立练习

完成一次“加载—观察墙体—观察相机目标—暂停—恢复”协同实验，并为每一步指出数据来源、ROS接口和RViz2显示项；运动、导航和碰撞留待AU9/AU10。

## 12 正常现象

- 若已有合法运动数据，Gazebo小车运动时RViz2模型同步变化；无运动前置时不以此判定AU8失败；
- 雷达点随姿态和环境变化；
- 相机画面随目标和朝向变化；
- 暂停仿真后基于仿真时间的数据停止更新；
- 恢复后链路继续工作；
- 地图中的墙与雷达点大致对齐。

## 13 常见问题定位顺序

1. Gazebo模型和传感器是否运行；
2. `/clock`是否更新；
3. Topic是否存在且有新消息；
4. 消息Frame和时间戳是否正确；
5. TF链是否连通；
6. 算法节点是否Active；
7. RViz2 Fixed Frame、Topic和QoS是否正确；
8. 显示属性是否把数据隐藏。

## 14 理解检查

1. Gazebo World和ROS Map为什么不是同一个对象？
2. 鼠标瞬移为什么会破坏协同判断？
3. `/clock`停止会影响哪些现象？
4. 相机黑屏时为什么不能只查RViz2？
5. SLAM和AMCL为什么不能同时发布`map→odom`？

## 15 技能检查与证据

提交协同链路图、Gazebo与RViz2同步截图、雷达和相机验证、暂停/恢复记录以及一次故障定位过程。能从现象追踪到Topic、TF和组件即可形成AU8学习结论；运动、导航和碰撞结果不作为AU8完成条件。

## 16 项目内依据

- `ai_robot_sim/launch/sim_bringup.launch.py`
- `ai_robot_description/urdf/ai_robot.urdf.xacro`
- M5 SLAM、定位与Nav2启动配置
