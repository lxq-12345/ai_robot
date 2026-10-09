# waypoint_navigation 用户操作与测试验收手册

- 版本：1.2
- 日期：2026-10-09
- 配套文件：plan/waypoint_navigation_需求与设计规范_v1.2.md、plan/waypoint_navigation_开发与测试项目计划_v1.4.md
- 当前状态：R00-C已冻结复用路线与接口；完整应用尚未开发，本手册是实现和验收基线，不代表新包、服务、参数已经存在。
- 适用环境：Ubuntu ROS 2/Nav2 仿真工作空间 `/home/ubuntu/ai_robot_ws`

## 1. 使用目标与接口约定

完整流程：启动仿真与 Nav2 → 确认定位 → RViz2 创建有序航点 → Publish Waypoints → 节点接收校验但不自动规划 → 用户请求规划 → 检查规划导航路径预览 → 用户请求执行 → 核对每个航点实际经过及最终结果或取消 → 保存配置 → 加载后重新请求规划。

已确认现有接口：`/waypoint_path` 为 `nav_msgs/msg/Path`，交互标记话题为 `/waypoint_plugin/feedback` 和 `/waypoint_plugin/update`。

待实现约定：包名 waypoint_navigation、节点名 waypoint_path_navigator、入口 waypoint_path_navigator；完整服务前缀为 `/waypoint_navigation`；预览话题 `/waypoint_navigation/prepared_path`；加载航点显示话题 `/waypoint_navigation/loaded_waypoints`；状态 `/waypoint_navigation/status`。若实际部署使用命名空间，以 ros2 service/topic list 查出的名称为准。

以下启动与服务命令只有开发完成、已冻结接口完成实现后才可使用。发布航点、加载配置、启动节点均不得自动启动规划或运动；规划和执行分别由用户显式请求。本手册采用R00-C选定的官方异步`ComputePathThroughPoses + FollowPath`路线。后续组件或接口变更须回到R00-C复核并升版。

## 2. 准备终端与环境

建议终端分工：A 启动现有仿真/Nav2；B 启动航点节点；C 操作服务；D 观察消息和记录证据。

本机Humble仿真每个新终端使用已经验证的环境入口（含工作空间、仿真本机DDS设置）：

```bash
cd /home/ubuntu/ai_robot_ws
source scripts/au9_sim_environment.sh
```

此入口使用本机loopback，不直接用于实体或跨机器部署；正式U01仍须核对适用环境。

沿用已经验证的机器人、地图、Nav2 和 RViz2 启动方式。本机已验证入口为`bash scripts/start_au9_manual_nav2.sh`，独立仿真停止入口为`bash scripts/stop_au9_manual_nav2.sh`。确认各终端 ROS_DOMAIN_ID、ROS 环境、网络发现及 use_sim_time 一致。

开发安装后执行：

```bash
cd ~/ai_robot_ws
colcon build --packages-select waypoint_navigation
source install/setup.bash
ros2 pkg executables waypoint_navigation
```

预期最后显示 waypoint_path_navigator 可执行入口。若包不存在，先完成开发，不继续调用新服务。

## 3. 启动仿真并完成基础检查

在终端 A 用项目现有命令启动仿真、Nav2 与 RViz2。记录命令、地图和参数版本。

```bash
echo $ROS_DISTRO
ros2 node list
ros2 action list -t
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 topic list -t
```

预期规划和控制服务器 active，存在 compute_path_through_poses 和 follow_path Action；如使用命名空间，替换相应名称。

确认 RViz2 Fixed Frame 为 map，地图、机器人与传感器显示对齐。需要时使用 2D Pose Estimate 设置初始位姿，方向与机器人实际朝向一致；确认 AMCL 定位稳定。

在没有本脚本任务的情况下，先使用 Nav2 Goal 完成一次普通目标导航。U01还必须完成T01-05选定FollowPath路线的反向朝向与绕墙基础关口，不能只凭普通目标成功忽略已知失败。完成后再进行本手册任务，后续不要同时从 Nav2 Goal 或其他导航客户端下发控制任务。

若基础导航失败，先修复定位、TF、Nav2 或速度链，不进入 FollowPath 验收。

## 4. 在 RViz2 创建航点

1. 显示 Waypoint Plugin 面板，工具栏选择 Waypoint Tool。具体添加菜单取决于已安装插件版本。
2. Topic 设置 `/waypoint_path`，Frame 设置 `map`，Default Height 设置 `0.00`；地面差速车一般不启用 6D。
3. 在已知可通行区域依次点击创建点，先使用两个清晰分开的航点，避免点位于墙体、障碍物或膨胀区域。
4. 切换 Interact 工具进行拖动和朝向调整。单点 X/Y/Z/Yaw 显示当前选中航点，不是整个集合。
5. 确认 Total waypoints 数量。路径顺序以实际发布的 poses 数组为准，不仅凭屏幕位置判断。
6. 不确定顺序或误加点时，Clear All 后重新按顺序创建。清除是配置操作，不是取消导航命令。

Yaw 通常以弧度表示；0 对应 map 的 +X，正角度绕 +Z 逆时针。地图屏幕旋转时，不能把屏幕上下直接当作坐标方向。

## 5. 发布并验证航点消息

终端 D 先运行：

```bash
ros2 topic echo /waypoint_path --once
```

再点击面板 Publish Waypoints。预期接收到一条 Path，顶层 frame_id 为 map，poses 含两个点。重点检查坐标、顺序和四元数；单点 header 空白由新节点按照规范处理。此处的Path是**有序航点快照**，不是供控制器直接跟踪的规划导航路径。Publish之后新节点只更新配置；在手动请求plan前不得发送规划Action目标或出现新的有效规划预览。

持续监听：

```bash
ros2 topic echo /waypoint_path
```

拖动反馈监听：

```bash
ros2 topic echo /waypoint_plugin/feedback
```

没有消息时检查：

```bash
ros2 topic info /waypoint_path --verbose
```

先确认按钮、话题、节点发现和 QoS。仅在发布者确实使用 transient_local 时尝试：

```bash
ros2 topic echo /waypoint_path --qos-durability transient_local --once
```

创建或拖动点不一定自动发布完整 Path，每次修改后重新点击 Publish Waypoints。

## 6. 启动航点导航节点（待实现）

终端 B 使用开发完成后提供的 launch：

```bash
ros2 launch waypoint_navigation waypoint_navigation.launch.py
```

launch 必须加载包内 navigator.yaml；仿真配置必须 use_sim_time=true，并填写实际 planner_id、controller_id、goal_checker_id、map_identity 和配置路径。不要照抄示例插件 ID。

检查：

```bash
ros2 node info /waypoint_navigation/waypoint_path_navigator
ros2 service list -t
ros2 topic echo /waypoint_navigation/status
```

冻结接口预期有 plan、execute、cancel、save、load 服务，类型均为 std_srvs/srv/Trigger；status 为含版本和任务信息的 JSON 字符串。启动时无导航任务，机器人不因节点启动而规划或运动。后续若调整已冻结接口，须先升版修订本手册再验收。

节点启动后再次点击 Publish Waypoints，确保当前配置被收到；不要假设之前一次性消息能被新订阅者获取。终端应显示航点数量和配置版本。

## 7. 规划与路径预览

终端 C：

```bash
ros2 service call /waypoint_navigation/plan std_srvs/srv/Trigger '{}'
```

服务响应只表示请求接受或拒绝，不等于规划成功。观察节点终端与 status，等待 READY 或明确失败；规划期间不得请求执行。

在 RViz2：Add → By topic → /waypoint_navigation/prepared_path → Path，设置明显颜色；另添加 /waypoint_path 的 Path 显示用于比较。加载配置时可显示 /waypoint_navigation/loaded_waypoints。

检查规划导航路径从机器人当前位置附近开始，依次进入各航点的U01规定位置范围，避开墙体，转弯合理，终点方向符合任务。两个稀疏航点之间规划结果可绕行，不应要求简单直线连接。预览经过航点不等于小车已实际经过。

确认：

```bash
ros2 topic echo /waypoint_navigation/prepared_path --once
```

若规划失败，不执行，依据日志调整航点或环境。若机器人移动、配置修改或路径过期，重新调用 plan。

## 8. 执行 FollowPath

确认没有其他导航任务、预览合理且状态 READY 后：

```bash
ros2 service call /waypoint_navigation/execute std_srvs/srv/Trigger '{}'
```

响应接受后继续观察实际目标是否被 Nav2 接受及最终结果。预期状态 EXECUTING，终端显示起点、任务 ID、进度与航点事件。

选定设计中的FollowPath连续跟踪路径。中途航点只验小车实际按顺序进入允许位置范围，不要求停车或达到指定朝向；最后一个航点验位置和朝向。最终成功必须同时有执行Action结果、逐点实际经过和终点验收证据；不能只凭Action成功、规划路径经过航点或屏幕上靠近终点。遇障可绕行，但无法通过某个必经点时任务失败，不自动重新规划或跳点。

执行期间不要再使用 Nav2 Goal，也不要修改影响当前任务的控制参数。新增不同航点配置进入待处理区，不自动替换当前路径；相同配置应忽略。

## 9. 取消与故障处理

```bash
ros2 service call /waypoint_navigation/cancel std_srvs/srv/Trigger '{}'
```

等待 CANCELING 后的终态。请求接受不证明小车已经停止；同时观察实际运动和现有速度状态。取消失败、超时或失联时，按项目独立安全停止措施处理，不马上发送新目标。

不要把关闭终端、Clear All、重新加载 YAML 当作急停。终端 Ctrl+C 不能作为可靠运动停止手段。

失败时保留任务 ID、失败阶段、Nav2 错误码和原始错误、最后位姿与时间。没有证据时，不把失败统一解释为障碍物。恢复环境后重新检查和规划，再显式执行。

## 10. 保存与加载配置

第一版设计采用节点参数 config_file 指定路径，Trigger 服务不携带文件名。目录需提前创建并可写：

```bash
mkdir -p ~/ai_robot_ws/config/waypoint_navigation
ros2 param set /waypoint_navigation/waypoint_path_navigator config_file "$HOME/ai_robot_ws/config/waypoint_navigation/waypoint_followpath.yaml"
ros2 service call /waypoint_navigation/save std_srvs/srv/Trigger '{}'
```

实现必须允许该参数更新；若部署将参数设为只读，则在启动配置中指定后重启节点，不能假定 param set 成功。

保存成功后查看 YAML：

```bash
cat ~/ai_robot_ws/config/waypoint_navigation/waypoint_followpath.yaml
```

内容应包含 schema、地图身份、frame、航点顺序与姿态、导航插件参数，不保存能自动恢复运动的任务状态。

加载：

```bash
ros2 service call /waypoint_navigation/load std_srvs/srv/Trigger '{}'
```

检查响应和恢复航点显示；文件或地图错误应保留旧有效配置。加载后只恢复并显示航点，旧规划预览失效，不自动规划或运动；按“手动plan → 新规划预览 → 手动execute”重新操作。更改文件名需要先修改参数，不要覆盖重要原文件做错误测试。

## 11. 测试准备与证据记录

正式验收必须先完成项目计划 U01–U10 的对应单元测试。以下是用户端到端验收，不代替单元、接口和竞态测试。

冻结指标：中途航点位置偏差、终点位置与朝向容差、规划超时、取消响应、路径最大年龄、起点偏移、障碍无法通过的失败判定、日志频率等；记录实际 ROS/Nav2、地图和配置版本。参数未冻结时只能记试运行，不能判正式通过。

每个用例记录前置条件、操作、预期、实际、结果和证据。命令示例：

```bash
ros2 bag record -o waypoint_acceptance_run01 /waypoint_path /waypoint_navigation/prepared_path /waypoint_navigation/status /amcl_pose /odom /tf /tf_static /clock
```

rosbag 话题按部署和证据目的调整；Action 结果和节点终端日志需另行保存。录制结束后正常停止 recorder。截图用于辅助，不单独证明任务成功。证据目录遵循项目 tests/README.md；不将大文件默认提交 Git。

## 12. 用户测试与验收用例

### AT01 基础闭环

前置：基础导航可用、节点空闲。操作：创建两个开放区域航点，发布，确认无自动规划，再手动请求plan、预览，再手动请求execute。预期：每阶段状态正确，只有plan后才出现规划Action目标和新预览，只有execute后才运动；实际按序进入航点位置范围，终点位置/朝向符合基线。证据：配置、预览、规划和执行Action、逐点位置、终态与误差。失败则检查对应开发单元，不跳过。

### AT02 多航点与绕墙

操作：创建三个有转弯航点，再测试墙体两侧的有序点。预期：规划路线绕开墙，小车实际按任务顺序进入每个中途航点位置范围，中途不停车且无需达到指定朝向；最终航点位置/朝向符合基线。开放、转弯、绕墙场景至少各连续成功3次，记录每次结果及逐点轨迹证据。

### AT03 重复 Publish 幂等

操作：在IDLE、READY和EXECUTING状态分别多次点击相同Publish；开发测试可自动重放相同数据100次。预期：首次有效Publish只更新配置，不自动规划；后续相同Publish不增加版本、不重复写文件、规划或创建执行目标，当前任务继续。仅观察日志不够，应核对规划和执行Action目标计数、有效处理计数或测试工具证据。

### AT04 修改配置与旧结果

操作：规划中提交新配置，执行中再提交不同配置。预期：旧规划结果不覆盖新版本；执行中的任务快照不变，新配置待处理；结束后不能自动执行新任务。人工操作不能覆盖所有时序，需要同时引用 U05 的竞态测试证据。

### AT05 取消与再次导航

操作：导航中调用 cancel，等待终态，重新规划后执行。预期：取消结果与实际运动分别记录，响应时间符合基线，新任务必须显式启动。取消未确认时不发送新目标。

### AT06 保存、重启、加载

操作：保存，结束当前任务，重启节点，加载，检查航点显示与旧规划失效，再手动请求plan、查看新规划预览，最后手动请求execute。预期：配置语义一致，重启及加载不自动规划或运动，重新执行成功。

### AT07 无效输入与文件

操作：在空闲状态使用测试工具提交空或非法航点；加载损坏 YAML 副本、未知版本副本、不同地图配置。预期：拒绝并说明原因，原有效配置不变，没有运动。不得破坏正式配置文件；不在实体环境用非法控制数据测试。

### AT08 不可达点与过期路径

操作：选择已知不可达点测试规划失败；另规划正常路径，等待超过有效期或在无任务时将机器人移动超过起点阈值，再执行。预期：规划失败或执行拒绝，提示调整/重新规划。移动方式使用已经验证的仿真操作，避免与导航同时控制。

### AT09 故障与障碍

仅在仿真安全场景中按开发测试步骤注入服务器失联、TF异常和动态障碍。允许绕障后仍按序实际经过全部航点；若障碍使某个必经点无法通过，预期任务失败、停止且不自动重规划或跳点。错误或未知状态应清楚，无无限重试和自动恢复运动；仅显示有证据的障碍事件。重启恢复后仍需重新检查和显式操作。禁止随意停止关键服务器冒充通用急停。

### AT10 过程报告

检查起点、目标清单、规划耗时、任务 ID、进度、航点范围事件、终态和失败原因。预期：估算有标记，错误码保留，进度限频，航点事件不重复，不把低速认定为障碍或位置接近认定为停车完成。

## 13. 验收记录与完成判定

| 用例 | 前置条件 | 实际操作 | 预期结果 | 实际结果 | 通过/失败/受阻 | 证据 |
|---|---|---|---|---|---|---|
| AT01 | 待填 | 待填 | 见正文 | 待填 | 未执行 | 待填 |

每项独立记录，附执行时间、版本、地图身份、配置指纹、任务 ID、测量值、修复及重测记录。所有必测用例通过、指标达标且无关键未解决缺陷，才判用户端综合验收通过。开发单元测试和独立安装复现也必须通过，才能判第一版交付完成。远端归档状态单独报告。

实体机器人测试不是本仿真验收的自动下一步，须另行确认现场条件、急停、看门狗和用户当次运动授权。

## 14. 常见问题定位

| 现象 | 排查顺序 |
|---|---|
| echo 收不到航点 | 先启动监听再 Publish，检查 Topic、QoS、节点发现和环境 |
| 新服务不存在 | 包是否已开发安装、是否 source、节点名和命名空间是否正确 |
| 规划失败 | 服务器状态、TF、定位、地图、航点可达性和插件 ID |
| 服务返回成功但未运动 | 仅代表请求接受；查看 READY/EXECUTING、Action 接受状态及错误 |
| 加载点不显示 | 添加 loaded_waypoints 的 Path 显示，不假设插件自动恢复编辑标记 |
| 路径突然失效 | 配置版本、路径年龄、机器人起点位移、TF和地图身份 |
| 取消后仍移动 | 检查取消终态、其他导航客户端和底盘链，使用独立安全措施 |
| 保存失败 | config_file 实际值、目录权限、磁盘与原子替换错误 |
| 航点经过事件缺失 | 定位是否可靠、阈值、顺序及实际路线是否进入范围 |

## 15. 正常退出

取消或等待任务终止，确认无活动导航与实际运动；按需要保存配置；结束日志/rosbag；关闭航点节点，再按项目正常顺序结束仿真和 Nav2。记录未完成任务及异常，不将终端退出误认为导航成功。

## 16. v1.2选型与接口修订

统一默认名称空间/waypoint_navigation：节点/waypoint_navigation/waypoint_path_navigator，服务/waypoint_navigation/plan等，状态/waypoint_navigation/status，预览/waypoint_navigation/prepared_path；输入/waypoint_path保持兼容，加载显示不回流。服务为相对名，不使用节点私有~/plan造成额外前缀。

R00-C最小闭环证据不代替U01、U02–U10及用户综合验收；目前不得调用尚未实现的新包服务。评估profile不作为通用默认，正式指标由U01冻结；反向/绕墙及Action成功而终点超差必须闭环。程序实现须保留原规划时刻作路径有效性检查，执行几何按当前TF转换，最终按新鲜map位置/朝向及实际轨迹判结果。
