# Gazebo与RViz2辅助学习计划 v1.10

> AU = Auxiliary Unit（辅助学习单元）
> 本计划是`plan/ROS2仿真机器人学习计划_v1.8.md`的辅助教学补充，由GPT桌面沟通材料整理而来。
> 正式教材入口：`learning/Gazebo与RViz2辅助/`。
> 适用环境：Ubuntu 22.04、ROS 2 Humble、Gazebo Classic、RViz2、Nav2、现有`ai_robot_ws`项目。
> 边界：不替代M0至M6主线学习计划，不新增工程里程碑或Gate，不授权实体机器人操作。

## 1. 计划定位

本计划补强主线学习中容易被自动测试覆盖但人工经验不足的部分：Gazebo Classic界面、RViz2配置、机器人和环境建模、传感器可视化、Nav2目标操作、多航点观察、GUI证据记录和常见问题定位。

主线计划回答“当前M/L工程能力是什么”；本辅助计划回答“学员怎样熟练使用Gazebo和RViz2观察、解释和留证”。两者互补，不合并编号。

当前项目状态下，本计划优先用于补齐`S1-1-M5-L4`的Gazebo/RViz2 GUI人工体验证据；M5-L4补齐后，可继续用于M6 GUI体验和`S1-1-G1`前的工具能力强化。

## 2. 总体学习目标

完成后学员应能够：

1. 区分Gazebo Classic、RViz2、ROS 2和Nav2的职责；
2. 使用Gazebo GUI观察物理世界、模型、传感器和仿真时间；
3. 使用RViz2配置Map、LaserScan、RobotModel、TF、Path、Image和Camera；
4. 解释`/clock`、Topic、QoS、TF和Frame对显示结果的影响；
5. 建立简单SDF模型和两房间测试World；
6. 对齐现有URDF/Xacro、Gazebo插件、Topic和Frame；
7. 完成初始位姿、单目标、取消、多航点和临时障碍观察；
8. 形成截图、日志、配置、操作过程和结论可追溯的人工证据。

AU5与AU6属于“定义与观察”单元：AU5定义机器人和传感器模型，AU6定义环境World并做静态结构检查。AU8也是数据观察单元，只验证Gazebo、ROS 2与RViz2的数据链。小车运动、单目标导航、取消和安全停车归AU9；障碍与碰撞综合观察归AU10。

## 3. 前置条件

学习前应确认：

- 当前只在仿真环境执行，不进入实体机器人；
- 已能加载ROS 2 Humble和项目安装空间；
- `ai_robot_description`和`ai_robot_sim`可被ROS 2找到；
- Gazebo Classic、RViz2、Nav2和项目Launch入口可用；
- 学员知道停止Launch、关闭GUI和清理残留进程的基本方法。

## 4. 学习单元

| 单元 | 名称 | 核心目标 | 当前教材 |
|---|---|---|---|
| AU1 | 产品介绍与基础认识 | 建立Gazebo/RViz2职责、版本边界、Classic/Sim命名与命令边界 | `source/AU1/AU1-01_产品介绍与基础认识_v1.3.md` |
| AU2 | 软件安装与环境检查 | 验证版本、依赖、构建和启动入口 | `source/AU2/AU2-01_软件安装与环境检查_v1.0.md` |
| AU3 | Gazebo界面与配置 | 掌握GUI、仿真控制、World和后台模式 | `source/AU3/AU3-01_Gazebo界面与配置_v1.0.md` |
| AU4 | Gazebo建模基础 | 理解SDF、Model、Link、Joint和三类属性 | `source/AU4/AU4-01_Gazebo建模基础_v1.0.md` |
| AU5 | 机器人与传感器建模 | 定义URDF/Xacro、SDF、插件、雷达、相机和IMU，并观察非运动接口 | `source/AU5/AU5-01_机器人与传感器建模_v1.1.md` |
| AU6 | 环境建模 | 定义可供后续导航使用的两房间World，完成静态Visual/Collision与视角检查 | `source/AU6/AU6-01_环境建模_v1.1.md` |
| AU7 | RViz2界面与配置 | 从空白界面配置项目观察视图，解释Topic/TF/QoS和显示状态，不执行导航 | `source/AU7/AU7-01_RViz2界面与配置_v1.1.md` |
| AU8 | Gazebo与RViz2协同 | 通过独立Gazebo、RViz2和检查入口追踪小黄车双目数据链及Gazebo重启恢复，不执行运动或导航 | `source/AU8/AU8-01_Gazebo与RViz2协同_v1.4.md` |
| AU9-01 | 导航操作与路径工具 | 操作初始位姿、单目标完整控制闭环、小车运动、取消及现有Nav2 `FollowWaypoints`多航点 | `source/AU9/AU9-01_导航操作与路径工具_v1.1.md` |
| AU9-02 | WaypointTool多航点规划与导航执行 | 接收`/waypoint_path`航点快照；用户分别请求规划和执行；按序实际经过航点并记录取消及结果 | 教材待R00-C选型后编写；有效需求与计划见`plan/waypoint_navigation_需求与设计规范_v1.1.md`和`plan/waypoint_navigation_开发与测试项目计划_v1.2.md` |
| AU10 | 综合测试练习 | 串联建图、定位、导航、障碍、相机和安全停车 | `source/AU10/AU10-01_综合测试练习_v1.0.md` |
| AU11 | 总结与考核 | 检查知识、操作、建模、协同、导航和证据 | `source/AU11/AU11-01_总结与考核_v1.0.md` |

## 5. 与M5/M6 GUI人工体验的衔接

AU9-02接在AU9-01已有导航链路之后，是AU9的新增工程与人工体验单元。原AU9-02自动用例使用Nav2`FollowWaypoints`直接提交固定航点，仍保留为已有能力证据；它不能证明RViz2`WaypointTool → /waypoint_path → 用户请求规划 → 预览 → 用户请求执行 → 小车按序实际经过航点`新闭环。新增单元按`plan/waypoint_navigation_开发与测试项目计划_v1.2.md`的R00、U01至U12实施；全部保留单元和验收完成即为用户确定的AU9完成边界，不另设圆环、拖拽或旋转遗留回归阻塞项。具体设计由R00-C根据固定需求冻结。

`S1-1-M5-L4`的GUI人工体验可从AU8、AU9和AU10分层抽取。AU8只覆盖第1至3项的启动与数据观察；第4至6项的导航和运动验证从AU9开始：

1. 启动Gazebo GUI和RViz2；
2. 设置或加载可用RViz2显示项；
3. 观察已有地图定位或SLAM状态；
4. 执行可达目标导航；
5. 执行中途取消并确认安全停车；
6. 观察路径、机器人模型、LaserScan、速度链和Gazebo实际运动；
7. 记录截图、日志、Action状态、进程清理和结论。

M6 GUI体验另行补充任务管理器反馈、到点感知、取消/超时/安全触发和同一`task_id`幂等重放，不混入M5-L4结论。

## 6. 证据与完成条件

每个AU完成时至少应有：

- 教材讲解记录；
- 理解检查结果；
- 学员独立人工练习结果；
- 截图、日志、配置或模型文件；
- 问题与排查记录；
- 明确结论：通过、需补学或未执行。

辅助课程全部完成的条件是AU1至AU11均有结论，且AU10/AU11覆盖M5/M6 GUI人工体验所需证据。主线M学习完成仍以`plan/ROS2仿真机器人学习计划_v1.8.md`和`mem/当前状态.md`为准。

## 7. 安全与变更边界

- 所有操作仅限Gazebo仿真；
- 不执行实体机器人上电、运动或硬件测试；
- 不绕过`cmd_vel_guard`直接发布运动控制命令；
- 不把鼠标拖动Gazebo机器人当作正常导航证据；
- 不将自动测试通过冒充GUI人工体验；
- 发现工程缺陷时先记录证据，再按项目流程单独处理。

---

**版本**：v1.10
**日期**：2026-10-04
**状态**：正式辅助学习计划；AU9增加waypoint_navigation单元，尚未实施或验收；既有AU9-01与FollowWaypoints测试保持原结论。
