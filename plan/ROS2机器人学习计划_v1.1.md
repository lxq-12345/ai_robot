# ROS 2机器人学习计划 v1.1

> 归属：《AI机器人开发项目计划_v1.10》的总计划补充。
> 当前范围：基于已完成的S1-1-M1、S1-1-M2成果，系统学习ROS 2机器人知识，并人工执行对应测试验收。
> 边界：仅使用既有Gazebo仿真、GUI与命令行入口；不接入AI Agent，不进行实体机器人上电、运动、控制命令或硬件测试。
> 定位：学习计划不是新的里程碑或Gate，不替代自动测试、S1-1-G1验收或实体安全授权。

## 1. 学习目标

学习完成后，学习者应能够：

1. 说明ROS 2工作空间、功能包、节点、Topic、Service、Action、消息、QoS与TF的作用及关系；
2. 说明本项目从`/cmd_vel_raw`到`/cmd_vel`、`/odom`与TF的仿真底盘数据流和安全边界；
3. 在既有仿真环境中独立启动M1、M2相关入口，观察关键现象并执行人工验收；
4. 使用项目证据模板记录命令、预期现象、实际观察、问题和结论。

## 2. 执行原则

- 先阅读既有成果，再执行人工复现；不得通过修改已验收实现来“制造”现象。
- 人工验收与既有自动测试相互补充；自动测试通过不自动等同于人工学习完成。
- 所有底盘演示仅限Gazebo仿真。不得直接发布`/cmd_vel`；M2演示必须使用既有`manual_motion_demo`入口。
- 每次学习完成后保存观察记录；发现异常时先保留日志与证据，再决定是否进入修复和回归。

## 3. 学习环境准备

在项目根目录执行：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
./scripts/build.sh
./scripts/test.sh
```

学习者应先确认构建与统一回归通过，再开始人工复现。标准测试入口会优先使用ROS 2 Humble已验证的系统Python环境。

## 4. S1-1-M1：资源、接口与测试基线

### 4.1 学习内容

- 阅读`resources/S1-1-M1对象资源矩阵.md`，理解机器人对象、候选资源、仿真实现、实体实现和测试方法的对应关系。
- 阅读`resources/S1-1-M1第三方资源卡与准入流程.md`，理解许可证、版本、接口、最小验证和安全准入。
- 阅读`config/ros_interface_baseline.yaml`与`config/tf_frame_baseline.yaml`，理解Topic、消息、QoS、命名和`map -> odom -> base_link -> sensor_link`坐标链。
- 阅读最小C++、Python功能包及其单元、契约和Launch测试，理解ROS 2包、节点和测试分层。

### 4.2 人工执行与观察

```bash
ros2 pkg executables ai_robot_cpp_example
ros2 pkg executables ai_robot_py_example
ros2 interface show geometry_msgs/msg/Twist
ros2 run tf2_tools view_frames
./scripts/test.sh
```

人工验收应确认：两个样例包可被发现；`Twist`包含线速度和角速度；TF报告可生成；统一测试入口通过；能够说明`reliable_depth_10`与`sensor_data` QoS的用途。

### 4.3 M1人工验收结论

通过条件：学习者能够解释资源矩阵、接口基线、TF责任边界和测试层级，并保存一次人工执行记录。未通过时，记录无法解释的概念、命令或现象，不影响既有M1自动验收结论。

## 5. S1-1-M2：仿真本体与差速底盘单元

### 5.1 学习内容

- 阅读`src/ai_robot_description/urdf/ai_robot.urdf.xacro`，理解`base_footprint`、`base_link`、左右轮和传感器Frame。
- 阅读`src/ai_robot_sim/ai_robot_sim/cmd_vel_guard.py`与`config/sim_base.yaml`，理解限速、命令超时和安全停车。
- 阅读`src/ai_robot_sim/launch/sim_bringup.launch.py`与`manual_motion_demo.py`，理解Gazebo、`robot_state_publisher`、差速插件和人工演示启动顺序。

### 5.2 人工执行与观察

终端一启动仿真：

```bash
ros2 launch ai_robot_sim sim_bringup.launch.py gui:=true
```

终端二运行人工演示：

```bash
ros2 run ai_robot_sim manual_motion_demo
```

终端三按需观察：

```bash
ros2 topic echo --once /odom
ros2 topic echo --once /joint_states
ros2 run tf2_ros tf2_echo odom base_link
```

人工验收应观察前进、停止、后退、停止、左转、停止、右转、停止；确认前进/后退时左右轮同向，转向时左右轮反向，`/odom`与`odom -> base_link`持续更新，演示停止后底盘保持停止。

### 5.3 M2人工验收结论

通过条件：学习者能够解释URDF/Xacro、差速驱动、`/cmd_vel_raw -> cmd_vel_guard -> /cmd_vel`、`/odom`和TF之间的关系，并完成一次人工演示观察与记录。不得直接向`/cmd_vel`或`/cmd_vel_raw`手工发布命令。

## 6. 记录与问题处理

每次人工学习与验收使用`tests/evidence/test_evidence_template.md`记录：学习主题、Git提交、执行命令、预期现象、实际观察、证据路径、结论和待解问题。需要录包时使用`tests/evidence/rosbag_record_template.md`。

发现问题时，按“现象 -> 日志/截图/rosbag -> 复现步骤 -> 影响 -> 修复或风险结论”记录；修复变更必须重新执行受影响的自动测试和人工复现。

## 7. 当前范围与后续扩展

本版仅覆盖S1-1-M1与S1-1-M2。S1-1-M3至S1-1-M6的系统学习与人工复现将在后续版本另行规划；本计划不改变S1-1-G1的验收标准、接口冻结要求、硬件审查要求或实体阶段准入结论。
