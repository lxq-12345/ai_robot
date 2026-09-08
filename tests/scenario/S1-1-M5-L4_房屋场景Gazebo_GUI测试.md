# S1-1-M5-L4 房屋场景Gazebo GUI测试

## 1. 目的与边界

本场景验证`apartment_house_merged_v1.3.world`能够通过项目安装空间启动Gazebo Classic图形界面、生成现有机器人并发布基础传感器和里程计数据。

测试仅限仿真，不发布运动命令，不构成实体机器人操作授权。脚本自动结果不能替代操作者对房屋外观、碰撞重叠和机器人稳定性的人工观察。

## 2. 前置条件

- `colcon build --packages-select ai_robot_sim`通过；
- `colcon test --packages-select ai_robot_sim`通过；
- 从Ubuntu图形桌面终端执行，`DISPLAY`有效；
- 执行前没有`gzserver`或`gzclient`残留进程。

## 3. 执行命令

启动GUI并持续显示：

```bash
cd /home/ubuntu/ai_robot_ws
./scripts/test_apartment_house_gui.sh
```

运行日志保存在`log/manual/apartment_house_gui_YYYYMMDD_HHMMSS.log`，属于本地构建/运行产物，不提交Git。

脚本不会按时间自动退出。完成观察后，在启动脚本的终端按`Ctrl+C`，或者关闭Gazebo窗口。

## 4. 自动检查

- `gzclient`图形进程已启动；
- Gazebo模型包含`apartment_house`、`ground`和`ai_robot`；
- 机器人位于推荐出生点`(1.80, 4.00)`允许误差范围内；
- `/scan`发布且Frame为`laser_link`；
- `/odom`发布且Frame为`odom`；
- 结束后脚本启动的Gazebo进程已退出。

## 5. 人工观察

1. 房屋墙体、五处门洞、阳台开口和东侧窗户能够显示；
2. 黄色四轮小车位于房屋内部，没有与墙体初始重叠；
3. 机器人静止稳定，没有抖动、翻飞、下沉或穿透地面；
4. GUI视角能够查看主体与北侧阳台区域；
5. 截图中应同时保留房屋整体和机器人位置。

相机操作顺序：

1. 按`Esc`回到选择模式，避免处于模型旋转、平移或缩放工具；
2. 在三维场景空白处按住鼠标中键拖动，使相机围绕观察点旋转；没有中键时按住`Shift`并用鼠标左键拖动；
3. 鼠标左键拖动用于平移视图；
4. 滚轮或鼠标右键拖动用于缩放；
5. 将相机从俯视逐步旋转到接近水平，不要使用工具栏的模型旋转按钮来旋转房屋。

## 6. 停止与异常处理

- 正常情况下脚本持续运行，不会限时退出；完成观察后按`Ctrl+C`或关闭Gazebo窗口，脚本随后清理Launch及其子进程；
- 提前停止使用`Ctrl-C`，不得使用广域`killall`清理其他用户进程；
- 若提示Gazebo已在运行，先确认并停止旧测试，再重新执行；
- 若失败，检查终端输出及脚本显示的日志文件，结论记录为“未通过”。

## 7. 通过标准与证据

自动检查全部显示`PASS`，人工观察五项均符合预期，退出后无相关残留进程，才能将本GUI场景记录为“通过”。建议证据写入：

```text
tests/evidence/S1-1-M5-L4_房屋场景Gazebo_GUI测试记录_YYYYMMDD.md
```
