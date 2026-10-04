# AU9 导航操作与路径工具测试

> 范围：仅限Gazebo仿真；复用AU8的`apartment_v1.3.world`、`small_yellow_car_v1.2.sdf`及其专用占用栅格地图。
> 安全：速度必须经`/cmd_vel_raw -> cmd_vel_guard -> /cmd_vel`；不直接发布两个速度Topic，不操作实体机器人。

## 1. 测试目标

验证AU9中的定位前置、单目标导航、多航点、运动中取消、安全停车、速度限幅和Gazebo/里程计反馈。

## 2. 案例矩阵

以下AU9-01至AU9-07是现有Nav2能力回归；其中AU9-02使用测试程序直接调用`FollowWaypoints`，不覆盖下文新增的WaypointTool/FollowPath单元。为避免编号混淆，新增单元测试使用`AU9-FP-*`编号。

| 编号 | 案例 | 操作 | 通过标准 |
|---|---|---|---|
| AU9-01 | 定位与生命周期 | 启动稳定世界、AMCL和Nav2，发布初始位姿 | `map -> odom`存在，BT Navigator和Waypoint Follower为Active |
| AU9-02 | 多航点 | 小黄车从`(1.80, 4.00)`出发，通过`FollowWaypoints`沿`+X`连续访问`(2.20, 4.00)`和`(2.60, 4.00)`，航点朝向与行驶方向一致 | Action为`SUCCEEDED`，无遗漏航点，里程计位移大于0.35 m |
| AU9-03 | 运动中取消 | 向`(1.80, 5.80)`发送单目标，确认已运动后取消 | 取消被接受，Action最终为`CANCELED` |
| AU9-04 | 取消后停车 | 取消后继续观察安全速度 | 0.5 s宽限后不再出现非零安全速度 |
| AU9-05 | 单目标导航 | 从取消点导航回`(1.80, 4.00)` | Action为`SUCCEEDED` |
| AU9-06 | 安全速度链 | 观察`/cmd_vel_raw`与`/cmd_vel` | 两端均有运动命令；安全线速度不超0.35 m/s，角速度不超1.20 rad/s |
| AU9-07 | GUI协同观察 | 在Gazebo和RViz2观察目标、路径、小车、雷达、代价地图 | 两个GUI与Action、TF、里程计现象一致 |

## 3. 自动实测

在干净环境执行：

```bash
cd /home/ubuntu/ai_robot_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
launch_test tests/integration/test_au9_navigation_tools.launch.py
```

该入口执行AU9-01至AU9-06，使用真实Gazebo、房屋地图、小黄车、AMCL、Nav2、Waypoint Follower和项目安全守卫，不使用假Action Server。

该命令默认同时显示Gazebo和RViz2，用于直接观察路径、小车运动、取消停车和返回过程。需在无图形界面的自动化环境运行时，显式关闭GUI：

```bash
AU9_TEST_GUI=false launch_test tests/integration/test_au9_navigation_tools.launch.py
```

无论是默认GUI模式还是显式无界面模式，均不改变航点、断言、安全速度链或超时。

## 4. 人工Nav2操作实测

在图形桌面的终端执行：

```bash
cd /home/ubuntu/ai_robot_ws
./scripts/start_au9_manual_nav2.sh
```

该脚本只启动环境，不会自动发送导航目标，也不会自动退出。等待约12–20 s，直到Gazebo小黄车、RViz2地图、雷达和代价地图稳定显示。Gazebo可见地面与Nav2地图共用`X=-0.50..6.70`、`Y=-0.50..8.00`边界，大范围物理地面碰撞保持不变。AU9专用RViz2配置使用`map`固定坐标系，`20 m × 20 m`参考Grid的Offset为`(0, 0, -0.01)`，与Gazebo `world`参考网格共用数值原点；仅将TopDownOrtho视图中心设在房屋地图中心`(3.10, 3.75)`。

人工操作步骤：

1. 确认RViz2的`Fixed Frame`为`map`，地图上的机器人位于出生点`(1.80, 4.00)`附近。
2. 如机器人、雷达与地图未对齐，使用RViz2工具栏的`2D Pose Estimate`，在`(1.80, 4.00)`附近沿`+X`方向拖动箭头。
3. 选择`Nav2 Goal`，先在`(2.20, 4.00)`附近沿`+X`方向拖动目标箭头。
4. 同时观察RViz2全局/局部路径与Gazebo小黄车转向、行驶和停车；第一目标到达后，再将目标设为`(2.60, 4.00)`。
5. 测试取消时，可向`(1.80, 5.80)`附近发送目标，小车开始运动后在Nav2面板点击`Cancel`，确认小车停止。
6. 完成后回到启动终端按`Ctrl+C`，等待Gazebo、RViz2和Nav2全部退出。

通过标准：

- RViz2可显示地图、机器人、LaserScan、全局/局部代价地图及路径；
- 两个`+X`目标均被Nav2接受，Gazebo和RViz2中的小黄车位移一致并在目标处停车；
- `Cancel`后路径执行终止，小车在短暂制动后保持停止；
- 运行期间不直接发布`/cmd_vel`或`/cmd_vel_raw`，所有运动均由Nav2 Action经安全链执行。

房屋出生点为`(1.80, 4.00)`，不应使用旧M5世界的目标坐标。人工拖动目标时以地图可通行区域为准，不要将目标放在墙体或障碍物中。

AI执行只记为技术实测；AU9-07的学员GUI个人证据仍需由学员操作和确认。

## 5. 失败与清理

- 任一案例失败时立即停止，保留首个失败和日志，不用后续结果覆盖。
- 先按`Ctrl+C`停止测试和Launch，再确认Gazebo、Nav2、RViz2与ROS 2节点无残留。
- 仅对明确的残留进程执行定向清理，不使用宽泛的`killall`或`pkill -9`。

## 6. 证据

记录Git提交、命令、每个案例结果、Action状态、里程计位移、速度限幅、GUI截图/观察、清理结果和最终结论。AU9-01至AU9-07是原有能力证据；AU9整体完成结论还须满足下文新增waypoint_navigation执行计划的全部保留单元及验收。

## 7. AU9新增WaypointTool/FollowPath单元（待开发）

前置：保留现有AU9-01至AU9-07结论；先完成`plan/waypoint_navigation_开发与测试项目计划_v1.2.md`中的资源调研、环境基线、候选实测与复用决策，再按选定范围实现。以下用例是目标验收，不表示当前已有`waypoint_navigation`包或服务。完成该计划全部保留单元及验收即为用户确定的AU9完成边界，不另设圆环、拖拽或旋转遗留回归阻塞项。

| 编号 | 场景 | 独立验收点 |
|---|---|---|
| AU9-FP-01 | RViz2 WaypointTool提交至少两个有序航点 | `/waypoint_path`为`nav_msgs/msg/Path`；接收端核对顺序、`map`参考系、姿态、重复提交与无效输入；发布配置不触发规划或运动 |
| AU9-FP-02 | 用户请求从当前位姿规划并预览 | 仅手动plan后出现规划Action目标；规划导航路径按序经过航点位置范围，RViz2显示预览；规划失败、过期路径和配置变化均不能进入执行 |
| AU9-FP-03 | 用户显式请求导航执行 | R00-C选定的真实Nav2 Action接收目标并形成终态；Gazebo小车按序实际进入每个中途航点位置范围，中途不停车或强制朝向，终点满足位置/朝向容差；里程计与安全速度链一致 |
| AU9-FP-04 | 运动中取消及再次执行 | 取消请求、Action终态和停车分别有证据；未知状态不发送新目标；再次执行需重新满足路径有效性条件 |
| AU9-FP-05 | 保存、重启与加载 | 航点配置往返一致，地图身份和配置版本可核对；加载不自动规划或运动，旧规划预览失效；与插件已有rosbag保存功能的边界明确 |
| AU9-FP-06 | 故障和并发 | 不可达点、服务器缺失、执行中修改配置、重复Publish、旧回调等情形有明确失败或拒绝，不产生双目标或自动接管；遇障无法经过必经点或实际漏点、乱序时任务失败且不自动重规划、跳点 |
| AU9-FP-07 | 学员GUI人工验收 | 学员独立完成设置、Publish、手动规划、预览、手动执行、取消，保存截图、Action状态、逐点轨迹和问题记录；自动测试不得替代人工结论 |

新单元采用包内测试、跨包集成测试及人工证据分层验收；测试入口待实现后写入，不预填虚构命令或结果。实际阈值在环境基线阶段冻结。所有导航仅限Gazebo仿真，速度必须经过项目安全守卫，不直接发布`/cmd_vel`或`/cmd_vel_raw`。既有AU9整体结论须同时说明原用例和新增单元的状态。
