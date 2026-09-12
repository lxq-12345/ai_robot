# AU7 RViz2界面与配置

> 对应计划：AU7

## 1 学习目标

- 认识RViz2窗口和主要面板；
- 掌握Fixed Frame、Display、Topic和QoS；
- 显示Grid、Map、LaserScan、RobotModel、TF、Path和Camera；
- 保存并重新加载项目专用RViz2配置；
- 能根据Status定位常见显示问题。

## 2 启动与职责边界

```bash
source /home/ubuntu/ai_robot_ws/install/setup.bash
rviz2
```

RViz2读取ROS 2消息和TF，不模拟碰撞、传感器或机器人动力学。它可以发送交互目标，但不负责真正的定位和路径规划。

## 3 窗口组成

常见区域包括：

- Displays：管理显示对象及属性；
- 中央三维视图：显示ROS数据；
- Views：设置Orbit、TopDownOrtho等视角；
- Time：显示ROS时间和墙钟时间；
- 工具栏：交互、测量、初始位姿、导航目标和点击点；
- Selection等可选面板。

## 4 Fixed Frame

Fixed Frame是所有显示数据变换到的参考坐标。建图、定位和导航通常使用`map`；只有里程计或机器人局部数据时也可能使用`odom`或`base_link`。

Fixed Frame错误会导致多个Display同时报错。遇到大面积红色Status，应先检查全局Fixed Frame和TF，而不是逐个调显示颜色。

## 5 两种添加入口

### 5.1 By Display Type

先选择想显示的对象类型，再手动配置Topic。适合学习和排错，层次是“显示什么—数据来自哪里”。

### 5.2 By Topic

先选择已有Topic，RViz2根据消息类型创建适合的Display。适合熟悉系统后的快速配置。

本课程统一以By Display Type为主，以便建立清晰的对象与Topic关系。

## 6 基本显示项

### 6.1 Grid

提供地面参考网格，无需Topic。

### 6.2 Map

Topic选择`/map`。正常时应显示分辨率、宽度、高度和地图原点。

### 6.3 LaserScan

Topic选择`/scan`。可调整点样式、大小、颜色转换和Decay Time。

### 6.4 RobotModel

从`robot_description`读取模型，并依赖TF确定各Link位置。

### 6.5 TF

显示坐标轴、箭头、名称和树。调试时打开名称，正常观察时可减少显示以避免拥挤。

### 6.6 Path与Odometry

Path显示规划轨迹，Odometry显示里程计位姿或轨迹。具体Topic取决于Nav2和项目配置，不能凭名称猜测，应从Topic列表确认。

## 7 相机显示

### 7.1 Image

选择`/camera/image_raw`，用于直接查看图像。

### 7.2 Camera

Camera Display结合图像、CameraInfo和TF显示相机视角及三维叠加关系。缺少CameraInfo或TF时可能报错，即使Image能够显示。

当前项目CameraInfo为`/camera/camera_info`，相机Frame为`camera_link`。

## 8 Topic与QoS

Display的Topic属性右侧通常可以选择或输入Topic。只点击左侧文字或Display名称不会进入编辑状态。

消息存在但RViz2收不到时，应检查QoS兼容性。传感器数据常使用Best Effort，地图等数据可能使用不同可靠性或持久性策略。不要在不理解的情况下只靠反复切换QoS碰运气，应先查看发布者信息。

```bash
ros2 topic info /scan -v
ros2 topic info /camera/image_raw -v
```

## 9 视角操作

- Orbit：三维环绕观察；
- TopDownOrtho：适合地图、路径和二维导航；
- Zero：重置当前视角参数；
- 鼠标滚轮：缩放；
- 平移与旋转：根据当前View控制方式操作。

俯视只是显示方式，不改变机器人和地图坐标。

## 10 标准项目配置

建议至少包含：

1. Grid；
2. Map，Topic `/map`；
3. LaserScan，Topic `/scan`；
4. RobotModel；
5. TF；
6. Path；
7. Image或Camera，Topic `/camera/image_raw`；
8. 与需要观察的局部/全局代价地图对应的Map显示。

不是所有任务都必须同时打开全部Display。相机与大量TF同时显示可能占用资源，应按任务启用。

## 11 保存与加载配置

通过File菜单使用Save Config As保存为项目专用`.rviz`文件。以后使用：

```bash
rviz2 -d /absolute/path/to/ai_robot_training.rviz
```

`.rviz`保存界面、显示项和Topic选择，不保存SLAM地图。地图仍由YAML和PGM等资源单独管理。

## 12 教师引导操作

1. 设置Fixed Frame为`map`；
2. 从By Display Type添加Map并设置`/map`；
3. 添加LaserScan并设置`/scan`；
4. 添加RobotModel和TF；
5. 添加Image并设置`/camera/image_raw`；
6. 切换TopDownOrtho；
7. 保存`.rviz`配置；
8. 关闭并用`-d`重新加载。

## 13 学员独立练习

从空白RViz2开始，建立标准项目配置，不使用By Topic。所有Display命名清晰，状态可解释，保存并重新加载成功。

## 14 正常现象与排错

- Fixed Frame正确且TF完整时Global Status为OK；
- Map有有效分辨率和尺寸；
- LaserScan点与地图墙体大致重合；
- RobotModel显示在正确位置；
- Image持续变化；
- Camera报错而Image正常时，优先检查CameraInfo和TF；
- Map分辨率为0时说明尚未收到有效地图；
- 显示重复通常是同一Display被添加两次，保留一份即可。

## 15 理解检查

1. Fixed Frame解决什么问题？
2. By Display Type和By Topic有什么区别？
3. Image和Camera Display的依赖有什么不同？
4. `.rviz`文件为什么不能代替地图YAML和PGM？
5. Topic存在但显示错误时应检查哪些层？

## 16 技能检查与证据

提交`.rviz`文件、Displays面板截图、地图与雷达俯视截图、相机截图和一次重新加载记录。所有核心Display可用且错误可解释，即可标记AU7完成。

## 17 项目内依据

- `/map`、`/scan`、`/camera/image_raw`、`/camera/camera_info`
- `ai_robot_description/urdf/ai_robot.urdf.xacro`
- M5 SLAM、定位和Nav2启动文件
