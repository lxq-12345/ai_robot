# PU1 项目总体架构与工程资源

版本：v1.0
对应计划：`plan/ROS2仿真机器人学习计划_v1.3.md`
对应单元：PU1
适用环境：Ubuntu 22.04、ROS 2 Humble、当前`ai_robot_ws`
教材状态：正式教材

## 1. 学习目标

完成本教材学习后，学员应能够：

- 说明AI层、任务接口层、ROS 2功能层、仿真执行层和未来硬件驱动层的职责边界；
- 说明底盘、传感器、建图、定位、导航和安全模块之间的关系；
- 说明上层任务如何通过ROS 2接口进入机器人系统；
- 找到工作空间中的程序包、配置、模型、地图、脚本、测试、规划和教材；
- 区分源文件、配置文件、项目资料与自动生成目录；
- 根据功能需求判断首先应检查的程序包或目录；
- 说明仿真实现与未来实体实现之间的主要替换关系。

本教材只讲解已经完成的阶段 1仿真机器人以及未来实体迁移边界，不实现AI Agent，不授权任何实体机器人操作。

## 2. 项目总体架构

### 2.1 五层结构

本项目采用分层结构：

```text
用户或测试程序
        |
        v
AI层（阶段 2，当前未实现）
        |
        | 受约束的结构化任务
        v
任务接口层
        |
        | Action、Service、受控Topic
        v
ROS 2功能层
        |
        +-------------------------+
        |                         |
        v                         v
仿真执行层                 未来硬件驱动层
Gazebo模型与插件            MCU、驱动器和实体传感器
```

这五层并非都在当前阶段运行。当前已经实现的是任务接口层、ROS 2功能层和仿真执行层；AI层属于阶段 2，硬件驱动层属于`S1-1-G1`通过后的`S1-2`实体子阶段。

### 2.2 AI层

未来AI层负责理解用户输入、形成高层任务并选择允许调用的机器人能力。它不负责底盘实时控制，也不能：

- 直接控制电机或电机驱动器；
- 直接发布`/cmd_vel`；
- 绕过Nav2、任务管理或安全监督；
- 自行执行任意Shell命令；
- 在未经确认时把语义地点随意转换为物理坐标。

当前学习阶段只认识这条边界，不读取AI Agent详细规划，不实现或启动AI组件。

### 2.3 任务接口层

任务接口层把上层意图转换为ROS 2机器人能够校验和执行的结构化任务。当前项目的核心接口是：

```text
src/ai_robot_interfaces/action/ExecuteCapabilityTask.action
```

核心执行节点是：

```text
src/ai_robot_sim/ai_robot_sim/capability_task_manager.py
```

任务管理器负责：

- 校验任务ID、能力名称、目标和超时；
- 检查所需传感器和安全状态；
- 调用Nav2执行导航；
- 反馈校验、导航和感知等阶段状态；
- 处理失败、取消、不可达、超时和安全触发；
- 返回结构化结果；
- 对重复任务执行幂等回放。

这个任务管理器属于阶段 1的非AI机器人能力层。它只接收结构化字段，不理解自然语言，也不调用大模型。

### 2.4 ROS 2功能层

ROS 2功能层是机器人软件主体。

| 功能模块 | 主要职责 | 当前项目位置或组件 |
|---|---|---|
| 机器人模型 | 描述车体、车轮、关节和传感器安装关系 | `ai_robot_description` |
| 底盘执行 | 接收安全速度并产生仿真运动、里程计和轮状态 | Gazebo差速插件 |
| 安全监督 | 限速、命令超时停车和传感器新鲜度检查 | `cmd_vel_guard.py` |
| 传感器 | 发布雷达、相机、IMU和轮状态 | Gazebo传感器插件 |
| 状态估计 | 融合里程计和IMU | `robot_localization` EKF |
| 建图 | 根据雷达、里程计和TF建立地图 | `slam_toolbox` |
| 定位 | 在已有地图中估计机器人位置 | AMCL |
| 导航 | 规划、控制、避障、恢复和取消 | Nav2 |
| 感知监测 | 检查雷达和相机数据链 | 项目传感器监测节点 |
| 任务管理 | 组织导航、到点感知和结果返回 | `capability_task_manager.py` |

模块间的核心依赖关系是：

```text
机器人模型与TF
    |
    +--> 底盘、传感器和可视化共同使用

底盘运动 --> /odom和odom->base_link
传感器 --> /scan、/camera/*、/imu/data

/odom + /imu/data --> EKF --> /odometry/filtered
/scan + /odom + TF --> SLAM --> /map和map->odom
地图 + AMCL + /scan + TF --> 定位
定位 + 地图 + 传感器 + 安全状态 --> Nav2
Nav2 + 到点感知 --> 任务管理器 --> 任务结果
```

### 2.5 仿真执行层

当前由Gazebo Classic模拟：

- 差速底盘和左右车轮；
- 激光雷达；
- 相机；
- IMU；
- 室内世界、静态障碍和临时障碍；
- 里程计和关节状态。

仿真层通过标准ROS 2接口向上提供能力，上层模块不应依赖Gazebo内部实现细节。

### 2.6 未来硬件驱动层

实体阶段将用真实设备替换Gazebo插件：

| 当前仿真实现 | 未来实体实现 |
|---|---|
| Gazebo差速底盘插件 | MCU、电机驱动器、编码器和底盘驱动 |
| Gazebo Ray传感器 | 实体激光雷达及ROS 2驱动 |
| Gazebo相机 | USB、RealSense或Orbbec等实体相机驱动 |
| Gazebo IMU | 实体IMU驱动 |
| 仿真故障注入 | 急停、电池、通信失联和设备诊断 |

原则上继续保留Topic、消息类型、TF名称、导航接口和任务结果语义。硬件协议、驱动、安装参数、标定、噪声、供电和安全回路必须在实体阶段重新实现和验收。

### 2.7 上层任务如何进入机器人

结构化能力任务的主链路是：

```text
测试程序或未来受约束的AI桥接层
    |
    | ExecuteCapabilityTask Action目标
    v
capability_task_manager
    |
    | 校验任务、目标、超时、传感器和安全条件
    v
Nav2 NavigateToPose Action
    |
    | 路径、控制和速度命令
    v
/cmd_vel_raw
    |
    v
cmd_vel_guard
    |
    | 限速和超时保护
    v
/cmd_vel
    |
    v
Gazebo差速底盘
    |
    +--> /odom、/joint_states、TF
    +--> 到点后读取雷达与相机状态
    |
    v
任务反馈和结构化结果
```

安全边界位于任务校验、Nav2控制、安全守卫和底盘执行等多个环节，不依赖单一节点。

## 3. 工作空间与目录

### 3.1 ROS 2工作空间

项目根目录是：

```text
/home/ubuntu/ai_robot_ws
```

ROS 2工作空间的四个核心目录是：

| 目录 | 来源 | 是否直接修改 | 作用 |
|---|---|---|---|
| `src/` | 项目源码 | 是，按项目流程修改 | ROS 2程序包和源文件 |
| `build/` | `colcon`生成 | 否 | 各包中间构建文件 |
| `install/` | `colcon`生成 | 否 | 安装结果和环境加载脚本 |
| `log/` | `colcon`生成 | 否 | 构建及测试日志 |

`build/`、`install/`和`log/`可以删除后重新生成，因此不能作为源文件或证据的唯一保存位置。

### 3.2 项目管理目录

| 目录 | 主要内容 |
|---|---|
| `plan/` | 当前有效规划 |
| `plan/bks/` | 历史规划版本 |
| `learning/` | 当前有效教材与教材管理规则 |
| `learning/bks/` | 历史教材版本 |
| `mem/` | 当前状态、阶段备忘和索引 |
| `skills/` | 会话和执行规则 |
| `docs/` | 本地参考资料，不上传GitHub |

### 3.3 工程资源目录

| 目录 | 主要内容 |
|---|---|
| `config/` | 接口、TF、传感器、EKF、SLAM、定位和仿真参数 |
| `resources/` | 对象资源矩阵和第三方资源准入资料 |
| `scripts/` | 环境检查、构建、测试和人工体验入口 |
| `tests/` | 单元、契约、Launch、场景和证据模板 |
| `src/ai_robot_sim/maps/` | 当前仿真导航地图 |
| `src/ai_robot_sim/worlds/` | Gazebo世界 |

### 3.4 只读识别命令

```bash
cd /home/ubuntu/ai_robot_ws
pwd
find . -maxdepth 2 -type d \
  -not -path './.git*' \
  -not -path './build/*' \
  -not -path './install/*' \
  -not -path './log/*' \
  | sort
```

这些命令只读取路径和目录，不修改工程基线。

## 4. 程序包与工程资源

### 4.1 当前项目程序包

执行`colcon list`可看到五个项目包：

| 程序包 | 构建类型 | 主要职责 |
|---|---|---|
| `ai_robot_cpp_example` | `ament_cmake` | 最小C++节点与工程样例 |
| `ai_robot_py_example` | `ament_python` | 最小Python节点与工程样例 |
| `ai_robot_description` | `ament_cmake` | URDF/Xacro机器人模型 |
| `ai_robot_interfaces` | `ament_cmake` | 项目自定义Action接口 |
| `ai_robot_sim` | `ament_python` | 仿真、安全、监测、导航入口和任务管理 |

规划中的`ai_robot_navigation`、`ai_robot_perception`、`ai_robot_hardware`和`ai_robot_agent`是职责边界或未来包名，不代表当前都已创建。判断实际包时以`colcon list`和`src/`为准。

### 4.2 三个代表包

#### `ai_robot_description`

```text
src/ai_robot_description/
├── CMakeLists.txt
├── package.xml
└── urdf/ai_robot.urdf.xacro
```

- `package.xml`声明包信息和依赖；
- `CMakeLists.txt`定义构建与安装；
- Xacro文件描述车体、车轮、传感器Frame、惯性和Gazebo插件。

#### `ai_robot_interfaces`

```text
src/ai_robot_interfaces/
├── CMakeLists.txt
├── package.xml
└── action/ExecuteCapabilityTask.action
```

Action文件定义目标、反馈和结果，是任务管理器与调用端的结构化契约。

#### `ai_robot_sim`

```text
src/ai_robot_sim/
├── ai_robot_sim/       # Python节点
├── launch/             # 仿真、SLAM、定位、Nav2和M6启动入口
├── maps/               # 地图
├── worlds/             # Gazebo世界
├── package.xml
├── setup.cfg
└── setup.py
```

其中：

- `cmd_vel_guard.py`负责速度安全路径；
- `manual_motion_demo.py`提供受控仿真运动序列；
- `scan_obstacle_monitor.py`和`camera_image_monitor.py`检查传感器链；
- `capability_task_manager.py`执行结构化能力任务；
- `sim_bringup.launch.py`是基础仿真入口；
- `m6_bringup.launch.py`是综合任务入口。

`__pycache__/`和`.pyc`属于Python自动缓存，不是应直接修改的源码。

### 4.3 第三方资源与项目代码

本项目优先使用成熟资源：

- Gazebo及`gazebo_ros`插件；
- `robot_state_publisher`和`tf2`；
- `robot_localization`；
- `slam_toolbox`；
- AMCL和Nav2；
- `rosbag2`、RViz2及ROS 2 CLI。

项目自研内容主要负责：

- 接口和命名基线；
- 参数和启动编排；
- 安全薄封装；
- 传感器状态监测；
- 结构化任务管理；
- 契约、故障注入和场景测试；
- 仿真与未来实体的统一边界。

第三方资源不能因“成熟”而免除准入。资源来源、许可证、版本、接口、测试和回退方式按`resources/S1-1-M1第三方资源卡与准入流程.md`记录。

## 5. 对象与链路概览

### 5.1 ROS 2对象

| 对象 | 本项目中的作用 |
|---|---|
| Node | 承担单一运行职责，例如安全守卫或任务管理 |
| Topic | 传输持续数据，例如速度、里程计和传感器流 |
| Message | 定义Topic数据结构 |
| Service | 处理短时请求与响应 |
| Action | 处理长时任务、反馈、取消和结果 |
| Parameter | 配置节点行为 |
| TF | 表示坐标系之间随时间变化或静态的关系 |
| Launch | 组合启动多个节点、参数和依赖 |

### 5.2 主要Topic和接口

当前接口基线位于`config/ros_interface_baseline.yaml`。

| 接口 | 类型 | 作用 |
|---|---|---|
| `/cmd_vel_raw` | `geometry_msgs/msg/Twist` | Nav2或受控演示产生的原始速度请求 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 安全守卫输出给底盘的速度 |
| `/odom` | `nav_msgs/msg/Odometry` | 底盘里程计 |
| `/scan` | `sensor_msgs/msg/LaserScan` | 激光扫描 |
| `/camera/image_raw` | `sensor_msgs/msg/Image` | 原始图像 |
| `/camera/camera_info` | `sensor_msgs/msg/CameraInfo` | 相机内参 |
| `/imu/data` | `sensor_msgs/msg/Imu` | IMU数据 |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | 诊断状态 |
| `ExecuteCapabilityTask` | 项目Action | 结构化机器人能力任务 |

接口基线中的`/cmd_vel`所有者写作安全监督者，表示只有经过安全处理的路径可以向底盘发布速度。

### 5.3 TF链

TF基线位于`config/tf_frame_baseline.yaml`：

```text
map
└── odom
    └── base_link
        ├── laser_link
        ├── camera_link
        └── imu_link
```

- `map -> odom`只由SLAM或定位系统发布；
- `odom -> base_link`只由底盘里程计或状态估计发布；
- `base_link -> sensor_link`由机器人模型通过`robot_state_publisher`发布；
- 同一父子变换禁止多个发布者同时负责。

### 5.4 四条核心链路

#### 运动控制链

```text
Nav2或manual_motion_demo
→ /cmd_vel_raw
→ cmd_vel_guard
→ /cmd_vel
→ Gazebo底盘
```

#### 状态反馈链

```text
Gazebo底盘
→ /joint_states和/odom
→ TF与状态估计
→ 定位、导航、诊断和任务反馈
```

#### 传感器数据链

```text
Gazebo雷达、相机和IMU
→ 标准传感器Topic
→ 监测、融合、SLAM、定位和Nav2
```

#### 导航任务链

```text
结构化任务
→ capability_task_manager
→ Nav2 Action
→ 规划与控制
→ 安全速度链
→ 底盘
→ 反馈、感知和结果
```

## 6. 实体迁移概览

### 6.1 原则上保留

- 上层机器人能力接口；
- Topic和消息类型；
- Action目标、反馈和结果语义；
- `map -> odom -> base_link -> sensor_link`坐标系职责；
- Nav2、任务管理和诊断的主要软件边界；
- 契约测试的公共部分。

### 6.2 必须替换或重新配置

- Gazebo模型和插件换成实体驱动；
- 轮径、轮距、速度和转向参数按实物标定；
- 雷达、相机和IMU安装外参按实物测量；
- 时间戳、噪声和协方差按实体数据调整；
- USB、Ethernet、串口或CAN通信链路；
- 电源、电池、保险、急停和失联停车机制；
- 实体低速、架空、限定区域和长稳测试。

### 6.3 实体迁移判断原则

若更换底层驱动迫使任务接口、公共Topic或TF职责发生无计划变化，应先检查是否出现架构泄漏，而不是直接修改上层系统适配单一硬件。

## 7. 常见问题与首查位置

| 现象 | 首先检查 |
|---|---|
| 找不到项目包 | 是否加载`/opt/ros/humble/setup.bash`和`install/setup.bash` |
| 修改源码后运行结果未变化 | 是否重新构建并重新加载工作空间 |
| Topic存在但没有数据 | 发布节点、消息类型、QoS、时间戳和上游数据 |
| TF不连通 | Frame名称、发布者职责和重复发布 |
| 机器人不运动 | 任务或演示入口、`/cmd_vel_raw`、安全守卫、`/cmd_vel`和Gazebo插件 |
| 导航失败 | 地图、定位、TF、代价地图、传感器、安全状态和Nav2日志 |
| Python目录出现`__pycache__` | 正常自动缓存，不作为源码修改 |

## 8. 术语表

| 术语 | 含义 |
|---|---|
| 工作空间 | 由`colcon`管理的一组ROS 2程序包及构建结果 |
| 程序包 | ROS 2中组织源码、依赖、接口和资源的基本单元 |
| 节点 | 运行时承担单一职责的ROS 2参与者 |
| ROS图 | 节点及其Topic、Service、Action等连接形成的运行网络 |
| TF | ROS 2中的坐标变换系统 |
| QoS | ROS 2通信的可靠性、历史、深度和持久性策略 |
| Launch | 声明并编排多节点系统启动的机制 |
| 仿真插件 | 在Gazebo中模拟底盘或传感器并连接ROS 2的组件 |
| 契约测试 | 验证接口名称、类型、QoS、TF或行为约定的测试 |

## 9. 学习要点总结

1. ROS 2功能层是当前机器人系统主体。
2. 任务接口层只接受结构化能力请求，不等同于AI Agent。
3. 仿真执行层和未来硬件驱动层应共享稳定的上层接口。
4. `src/`是源码，`build/`、`install/`和`log/`是可再生目录。
5. 当前实际存在五个项目包，规划中的未来包不能当成已实现事实。
6. 运动必须经过`/cmd_vel_raw -> cmd_vel_guard -> /cmd_vel`安全链。
7. TF发布职责必须唯一且满足`map -> odom -> base_link -> sensor_link`。
8. 外部资料用于扩展理解，项目实际代码、配置和测试证据是当前实现依据。

## 10. 正式练习前理解检查

进入PU1实际练习前，学员应能用自己的话回答：

1. 五个系统层分别负责什么，哪些层当前尚未开发？
2. 为什么任务管理器不是AI Agent？
3. 底盘、传感器、SLAM、定位、Nav2和安全守卫如何协作？
4. 为什么不能直接修改`build/`、`install/`和`log/`？
5. 仿真迁移实体时，哪些接口应保留，哪些实现必须替换？

不能解释的条目先返回对应章节补学，不直接进入正式练习。

## 11. 项目内依据

- `plan/AI机器人开发项目计划_v1.12.md`
- `plan/ROS2机器人开发规划_v1.7.md`
- `plan/ROS2仿真机器人学习计划_v1.3.md`
- `resources/S1-1-M1对象资源矩阵.md`
- `resources/S1-1-M1第三方资源卡与准入流程.md`
- `config/ros_interface_baseline.yaml`
- `config/tf_frame_baseline.yaml`
- `src/ai_robot_description/urdf/ai_robot.urdf.xacro`
- `src/ai_robot_interfaces/action/ExecuteCapabilityTask.action`
- `src/ai_robot_sim/`
- `tests/contract/`
- `tests/launch/`
- `tests/evidence/test_evidence_template.md`

## 12. 外部参考资料

| 资料名称 | 来源 | 适用版本 | 用途 | 链接 | 查阅日期 |
|---|---|---|---|---|---|
| Interfaces: topics, services, actions | ROS 2官方文档 | Humble | 理解ROS 2通信接口差异 | https://docs.ros.org/en/humble/Concepts/Basic/Interfaces-Topics-Services-Actions.html | 2026-07-29 |
| Understanding nodes | ROS 2官方文档 | Humble | 理解节点和ROS图 | https://docs.ros.org/en/humble/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Nodes/Understanding-ROS2-Nodes.html | 2026-07-29 |
| URDF tutorials | ROS 2官方文档 | Humble | 理解机器人模型、Link、Joint和`robot_state_publisher` | https://docs.ros.org/en/humble/Tutorials/URDF/ | 2026-07-29 |
| Navigation Concepts | Nav2官方文档 | Nav2 | 理解导航、Action和`map -> odom -> base_link`职责 | https://docs.nav2.org/concepts/ | 2026-07-29 |

外部资料描述通用ROS 2与Nav2机制。本项目的节点名称、安全速度链、任务接口和文件位置以本教材“项目内依据”列出的当前文件为准。
