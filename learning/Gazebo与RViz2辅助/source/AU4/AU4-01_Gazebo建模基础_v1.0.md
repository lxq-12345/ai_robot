# AU4 Gazebo建模基础

> 对应计划：AU4

## 1 本单元定位

AU4讲机器人建模和环境建模共同使用的语言与元素。AU5用这些知识造小车，AU6用这些知识造场地。

## 2 学习目标

- 认识SDF模型和资源目录；
- 理解Model、Link、Joint层级；
- 区分Visual、Collision、Inertial；
- 能设置位姿、尺寸、质量、材质和基本物理属性；
- 能建立并验证一个简单模型。

## 3 模型文件组织

Gazebo Classic自定义模型通常包含：

```text
my_box/
├── model.config
└── model.sdf
```

`model.config`描述模型名称、版本和入口文件；`model.sdf`描述模型结构。网格、贴图和材质可放在`meshes/`、`materials/`等子目录。

模型目录需要位于Gazebo能够搜索的位置，或通过模型路径配置引入。教材练习建议把模型保存在项目专用资源目录，而不是修改系统模型库。

## 4 SDF基本层级

常见层级为：

```text
sdf
└── model
    └── link
        ├── visual
        ├── collision
        └── inertial
```

模型可以有多个Link，并通过Joint连接。静态环境物体可设置为`static`，移动机器人通常不是静态模型。

## 5 核心元素

### 5.1 Model

一个可复用实体，例如方箱、桌子或整台机器人。Model有名称和世界位姿。

### 5.2 Link

具有几何、碰撞和惯性属性的刚体。一个模型至少需要一个Link。

### 5.3 Joint

约束两个Link的相对运动。常见类型包括fixed、revolute和continuous。

### 5.4 Visual

控制看起来是什么样。Visual错误可能只影响外观，不一定影响碰撞。

### 5.5 Collision

控制物理碰撞形状。为了稳定和性能，碰撞几何通常比精细外观简单。

### 5.6 Inertial

描述质量、质心和惯性矩。动态模型缺失或使用不合理惯性时，可能抖动、翻飞或穿模。

## 6 位姿和坐标

位姿通常由`x y z roll pitch yaw`表示。必须明确它相对父元素还是世界坐标。单位为米和弧度。

建立模型时先从原点和轴方向简单的结构开始，再逐步增加偏移和旋转，以减少坐标错误。

## 7 几何、材质与物理

基础几何包括box、cylinder、sphere和mesh。视觉几何与碰撞几何可以不同，但两者位置应合理对齐。

材质只影响显示；摩擦、弹性、接触和质量影响物理行为。学习时每次只调整一类参数并观察变化。

## 8 简单方箱示例

`model.config`：

```xml
<?xml version="1.0"?>
<model>
  <name>training_box</name>
  <version>1.0</version>
  <sdf version="1.6">model.sdf</sdf>
  <description>AU4 simple training box.</description>
</model>
```

`model.sdf`：

```xml
<?xml version="1.0"?>
<sdf version="1.6">
  <model name="training_box">
    <static>false</static>
    <link name="box_link">
      <pose>0 0 0.25 0 0 0</pose>
      <inertial>
        <mass>1.0</mass>
        <inertia>
          <ixx>0.0417</ixx><iyy>0.0417</iyy><izz>0.0417</izz>
          <ixy>0</ixy><ixz>0</ixz><iyz>0</iyz>
        </inertia>
      </inertial>
      <visual name="box_visual">
        <geometry><box><size>0.5 0.5 0.5</size></box></geometry>
        <material><ambient>0.1 0.4 0.8 1</ambient></material>
      </visual>
      <collision name="box_collision">
        <geometry><box><size>0.5 0.5 0.5</size></box></geometry>
      </collision>
    </link>
  </model>
</sdf>
```

## 9 教师引导操作

1. 建立模型目录；
2. 创建`model.config`和`model.sdf`；
3. 将模型加入Gazebo资源路径；
4. 插入模型并观察落地；
5. 暂停后检查外观和碰撞对齐；
6. 修改颜色、尺寸或质量，每次只改一项并重新验证。

## 10 学员独立练习

复制方箱模型并改成一个矮长障碍物。要求Visual、Collision和Inertial都存在，模型能落地且不出现明显抖动。

## 11 正常现象与排错

- 模型受重力落到地面；
- Visual和Collision位置基本一致；
- 动态模型不会无故飞出；
- 找不到模型时检查资源路径和`model.config`；
- 穿透或悬空时检查碰撞几何和位姿；
- 抖动时检查质量、惯性、接触和初始重叠。

## 12 理解检查

1. Visual和Collision为什么要分开？
2. Inertial缺失会有什么风险？
3. 静态模型和动态模型有什么区别？
4. Link和Joint分别表示什么？
5. 为什么复杂网格不一定适合作为碰撞几何？

## 13 技能检查与证据

提交模型目录、Gazebo截图和一次参数修改前后对比。模型可加载、可碰撞、物理稳定，并能解释三个核心属性，即可标记AU4完成。

## 14 项目内依据

- `ai_robot_description/urdf/ai_robot.urdf.xacro`
- Gazebo Classic SDF模型格式
