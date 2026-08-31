# Gazebo与RViz2辅助课程

版本：v1.0

## 1. 课程定位

本课程是与GPT桌面沟通形成的辅助教学单元课程，用于补充`plan/ROS2仿真机器人学习计划_v1.8.md`。它不替代`S1-1-M0`至`S1-1-M6`主线学习计划，不改变当前唯一执行目标，也不新增工程里程碑或Gate。

辅助课程重点补强Gazebo Classic、RViz2、建模、可视化、导航交互和GUI人工证据能力。当前阶段优先服务`S1-1-M5-L4`遗留的Gazebo/RViz2 GUI人工体验证据；后续可继续服务`S1-1-M6`人工体验和`S1-1-G1`仿真能力验收准备。

## 2. 目录结构

```text
learning/Gazebo与RViz2辅助/
├── README.md
├── Gazebo与RViz2辅助学习计划_v1.2.md
├── source/AU*/     # AU1至AU11 Markdown教材
├── html/AU*/       # 同版本HTML阅读版
├── assets/         # 后续图片和模型资源
└── bks/            # 历史版本归档
```

`docs/Gazebo与RViz2辅助教材/`保留为原始沟通材料或参考草稿；正式学习入口以本目录为准。

## 3. 覆盖矩阵

| 辅助单元 | 当前教材 | 主要能力 | 与主线关系 |
|---|---|---|---|
| AU1 | `source/AU1/AU1-01_产品介绍与基础认识_v1.0.md` | Gazebo/RViz2产品、历史、职责边界 | 建立GUI工具总认识 |
| AU2 | `source/AU2/AU2-01_软件安装与环境检查_v1.0.md` | 版本、安装、工作区环境检查 | 支撑所有GUI练习 |
| AU3 | `source/AU3/AU3-01_Gazebo界面与配置_v1.0.md` | Gazebo GUI、仿真控制、World入口 | 支撑M2至M6人工观察 |
| AU4 | `source/AU4/AU4-01_Gazebo建模基础_v1.0.md` | SDF、Model、Link、Visual/Collision/Inertial | 支撑环境和障碍物理解 |
| AU5 | `source/AU5/AU5-01_机器人与传感器建模_v1.0.md` | URDF/Xacro、插件、雷达、相机、IMU | 对齐M2/M3模型和传感器 |
| AU6 | `source/AU6/AU6-01_环境建模_v1.0.md` | 两房间World、墙体、障碍、相机目标 | 支撑M5导航场景 |
| AU7 | `source/AU7/AU7-01_RViz2界面与配置_v1.0.md` | Fixed Frame、Display、Topic、QoS、配置保存 | 支撑M3至M6 RViz2观察 |
| AU8 | `source/AU8/AU8-01_Gazebo与RViz2协同_v1.0.md` | `/clock`、TF、Topic、双界面同步 | 直接支撑M5-L4 GUI证据 |
| AU9 | `source/AU9/AU9-01_导航操作与路径工具_v1.0.md` | 初始位姿、单目标、多航点、取消 | 直接支撑M5/M6 GUI体验 |
| AU10 | `source/AU10/AU10-01_综合测试练习_v1.0.md` | 建图、定位、导航、障碍、相机、安全停车 | 当前M5-L4 GUI补证据主入口 |
| AU11 | `source/AU11/AU11-01_总结与考核_v1.0.md` | 知识、操作、建模、协同和证据考核 | S1-1-G1前工具能力检查 |

## 4. 执行顺序

完整辅助课程按AU1至AU11顺序学习。若当前唯一执行目标只是补齐`S1-1-M5-L4` GUI人工体验，可以优先使用AU8、AU9和AU10中与M5相关的操作与证据要求，不把AU1至AU11全部完成作为M5-L4补证据的前置条件。

## 5. 证据规则

AU学习证据优先保存到`tests/evidence/`，文件名应能体现AU编号、主线关联和日期。当前M5-L4补证据建议形成：

```text
tests/evidence/S1-1-M5-L4_Gazebo_RViz2_GUI人工体验记录_YYYYMMDD.md
```

证据至少记录项目版本、环境、启动命令、人工操作、预期现象、实际现象、截图/日志、进程清理、结论和待补问题。

## 6. 完成边界

AU课程完成表示学员掌握当前仿真项目中的Gazebo/RViz2实践能力，不等于`S1-1-G1`已通过，不构成实体机器人操作授权，也不表示已经迁移到新版Gazebo Sim。
