# waypoint_navigation 需求与设计规范说明书

- 文档版本：1.2
- 日期：2026-10-09
- 状态：R00-C已冻结复用路线、架构与接口；完整应用尚未实现，正式指标和功能验收未完成
- 主入口：`waypoint_path_navigator.py`
- 适用对象：现有 RViz2、Nav2 环境中的室内差速轮式小车，优先仿真验证

## 1. 目标与范围

用户在 RViz2 Waypoint Plugin 中设置有序航点，点击 Publish Waypoints 提交完整航点配置。新进程接收并检查配置，**不因接收或加载而自动规划**。用户单独请求规划后，系统从机器人当前位置生成经过这些航点的导航路径并发布预览；用户再次单独请求执行后，系统才调用选定的Nav2导航接口，持续报告进度，支持取消、保存和加载配置。R00-C选择官方异步Action薄适配：`ComputePathThroughPoses`规划与`FollowPath`执行；不把Simple Commander作为生产入口。

第一版交付闭环：提交航点 → 校验与去重 → **用户请求规划** → 规划导航路径并预览 → **用户请求执行** → 结果或取消。WaypointTool发布的`/waypoint_path`虽使用`nav_msgs/msg/Path`类型，在此处表示有序航点快照，不是已规划、可直接执行的稠密导航路径。

第一版包含：配置管理、受用户请求的规划、预览、受用户请求的执行、取消、终端报告、超时、状态管理和文件持久化。后续扩展包含：自动重新规划、RViz2 专用控制面板、逐点停车与动作。执行中允许Nav2在障碍附近规避绕行，但不得跳过航点；无法按序通过时任务失败，不自动重新规划或继续后续航点。接收或加载配置均不自动规划、执行或启动运动。

## 2. 已知环境与待确认项

已知输入话题为 `/waypoint_path`，类型 `nav_msgs/msg/Path`；交互标记话题为 `/waypoint_plugin/feedback` 和 `/waypoint_plugin/update`；地图参考系为 `map`。配置中的单点 header 可能为空，Z 和四元数分量可能存在浮点误差。

现有话题列表显示 planner_server、controller_server、AMCL、smoother_server 等相关话题，但不能据此认定服务器已激活。实施前必须确认 ROS_DISTRO、Nav2 版本、Action 定义、插件 ID、TF 链、底盘参考系、仿真时间和速度链。不同版本的 Action 字段及反馈不同，禁止按最新版本硬编码所有字段。

检查命令：

```bash
echo $ROS_DISTRO
ros2 action list -t
ros2 interface show nav2_msgs/action/ComputePathThroughPoses
ros2 interface show nav2_msgs/action/FollowPath
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 topic info /waypoint_path --verbose
```

## 3. 概念和约束

航点是任务要求经过的有序位置；规划导航路径是可跟踪的中间位姿序列。选定设计中的FollowPath是Action，由controller_server执行，不是普通Topic。发布航点快照不等于发起规划，更不等于启动导航。

机器人必须按序实际进入每个中途航点的位置允许范围，中途不停车、不要求满足其指定朝向；最后一个航点按与Nav2 Goal同类的终点位置和朝向容差验收。规划路径经过航点或导航Action返回成功，均不能单独证明实际逐点经过。偏差值由U01结合现有仿真环境冻结。需要逐点停靠时应另行定义任务。遇障无法进入某个必经航点范围时判导航失败，不以跳点代替成功。

### 3.1 固定需求与可调整设计

第1节交付闭环、第3节航点语义及第5节功能行为是R00候选都必须满足的需求。以下架构、包结构、ROS外部接口及模块划分由R00-C依据R00-A/B及最小闭环证据冻结。后续若需更换选定组件或接口，返回R00-C复核并修订版本；固定需求不变。候选不能满足需求时记录差距、补适配或排除；拟改变需求须另行讨论，不作为普通选型处理。

## 4. 总体架构

以下为R00-C选定的集成架构；底层复用现有Nav2服务器，新增代码限于实际应用缺口。

```text
RViz2 Waypoint Plugin
  → /waypoint_path
  → navigator_node → task_manager（仅接收、校验、保存配置）
       ├─ waypoint_config：检查、标准化、指纹
       ├─ config_storage：YAML 保存与加载
       ├─ readiness_checker：时间、TF、服务器检查
       ├─ 用户请求plan → path_planner：ComputePathThroughPoses
       │    → /waypoint_navigation/prepared_path → RViz2 Path 显示
       ├─ 用户请求execute → path_executor：FollowPath、反馈、取消
       └─ navigation_reporter：状态、终端与日志
```

采用 ROS 2 Python 包和异步 Action 客户端。复用Nav2官方异步Action API，分别保存规划与执行目标句柄；不采用Simple Commander生产入口，不在订阅或服务回调中阻塞等待整项任务。服务器发现、响应和任务等待均有总截止时间。任务协调采用单一串行事件入口或等效互斥机制，确保回调并发不会破坏状态。

## 5. 功能需求

| ID | 功能 | 必须行为 |
|---|---|---|
| FR-01 | 航点接收 | 接收完整航点快照，Publish 视为提交，不假定存在独立结束消息；接收不自动发起规划或执行 |
| FR-02 | 配置检查 | 检查数量、数值、参考系和姿态，失败保持原有效配置 |
| FR-03 | 去重 | 内容相同不增加版本、不写文件、不自动重复规划或执行 |
| FR-04 | 环境检查 | 在规划和执行前检查 TF、时间、Action 就绪和适用状态 |
| FR-05 | 路径规划 | 仅在用户单独请求后，从当前位姿规划依次经过航点的路径；失败不得启动运动 |
| FR-06 | 路径预览 | 发布完整路径和就绪状态，允许 RViz2 查看 |
| FR-07 | 显式执行 | 仅在用户单独请求后执行当前有效、符合版本且未过期的规划导航路径 |
| FR-08 | 取消 | 支持规划与导航取消，处理请求拒绝、超时和终态 |
| FR-09 | 结果处理 | 区分目标拒绝、成功、失败、取消、通信未知；只有Action结果及按序实际经过所有航点、终点姿态同时满足条件才报告任务成功；漏点、乱序或遇障无法通过时报告失败 |
| FR-10 | 保存加载 | 保存航点和导航参数，加载检查后只恢复配置与航点显示，不自动规划或运动 |
| FR-11 | 状态管理 | 管理配置、规划结果和执行任务，防止旧回调覆盖新状态 |
| FR-12 | 过程显示 | 输出起点、进度、航点事件、已证实的障碍事件及失败原因 |
| FR-13 | 参数化 | 话题、Action、插件、超时和容差通过参数配置 |

## 6. 模块与目录

```text
src/waypoint_navigation/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/waypoint_navigation
├── waypoint_navigation/
│   ├── __init__.py
│   ├── waypoint_path_navigator.py
│   ├── navigator_node.py
│   ├── models.py
│   ├── waypoint_config.py
│   ├── config_storage.py
│   ├── readiness_checker.py
│   ├── path_planner.py
│   ├── path_executor.py
│   ├── task_manager.py
│   └── navigation_reporter.py
├── config/navigator.yaml
├── launch/waypoint_navigation.launch.py
├── docs/usage.md
└── test/
```

入口只负责初始化、装配和关闭。models 定义配置、规划快照、任务、状态及错误。纯数据校验与存储不依赖 ROS 节点。planner 和 executor 封装 Action，不自行启动下一个阶段。task_manager 是状态变化唯一协调者。reporter 消费事件，不直接控制机器人。

模块接口至少包含：validate/normalize/fingerprint、load/save、check_ready、plan/cancel_plan、execute/cancel_execution、handle_event、report。错误统一携带阶段、内部错误类型、原始 Nav2 错误码与信息、任务 ID 和配置版本。

## 7. ROS 外部接口

以下为R00-C冻结的外部接口。应用默认名称空间`/waypoint_navigation`，节点名`waypoint_path_navigator`；服务使用相对名plan/execute/cancel/save/load而非节点私有名，状态使用相对名status。完整节点名为`/waypoint_navigation/waypoint_path_navigator`。名称空间和话题可重映射；现有输入及Nav2后端默认绝对名称保持兼容。

| 接口 | 类型 | 说明 |
|---|---|---|
| `/waypoint_path` | nav_msgs/msg/Path 输入 | RViz2 航点快照 |
| `/waypoint_navigation/prepared_path` | nav_msgs/msg/Path 输出 | 当前有效规划预览 |
| `/waypoint_navigation/loaded_waypoints` | nav_msgs/msg/Path 输出 | 加载后的航点显示，不回发输入话题 |
| `/waypoint_navigation/plan` | std_srvs/srv/Trigger | 请求异步规划；返回接受状态，不表示规划成功 |
| `/waypoint_navigation/execute` | std_srvs/srv/Trigger | 请求执行；返回接受状态，不表示到达成功 |
| `/waypoint_navigation/cancel` | std_srvs/srv/Trigger | 请求取消；最终结果由状态接口报告 |
| `/waypoint_navigation/save`、`/waypoint_navigation/load` | 第一版 std_srvs/srv/Trigger | 使用参数指定配置路径，返回文件操作结果 |
| `/waypoint_navigation/status` | 第一版 std_msgs/msg/String | 发布有 schema_version 的 JSON 状态 |
| `/compute_path_through_poses` | Nav2 Action 客户端 | 生成路径 |
| `/follow_path` | Nav2 Action 客户端 | 执行跟踪 |

后续可用自定义服务支持每次请求指定文件路径，使用自定义状态消息替代 JSON。扩展必须有接口版本策略。

输入 QoS 根据插件实际发布者配置选择；不要盲目使用 transient_local。预览和当前状态推荐 reliable、transient_local、depth=1。清除或失效时发布空预览并更新状态，避免旧图误导用户。即使订阅收到保留的旧配置，也不得自动运动。

## 8. 数据模型和 YAML 规范

建议文件名 `waypoint_followpath.yaml`；UTF-8 编码，使用安全 YAML 解析，不允许任意对象构造。

```yaml
schema_version: 1
name: example_route
frame_id: map
map_identity: apartment_v1
navigation:
  planner_id: GridBased
  controller_id: FollowPath
  goal_checker_id: ''
waypoints:
  - position: {x: 4.3164, y: 5.8057, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 0.46255, w: 0.88659}
  - position: {x: 4.7050, y: 1.7269, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: -0.71465, w: 0.69948}
```

上述插件 ID 和地图标识仅为示例，必须匹配实际配置。扩展版本字段如 progress_checker_id，仅在本机接口支持时启用。保存配置不包含可直接恢复运动的执行状态；可另存规划路径用于诊断，但不能作为重启后自动执行依据。

map_identity 使用明确配置的地图标识或地图元数据及内容摘要。相同 frame_id 不足以证明地图一致。未知地图身份显示未验证状态；第一版默认阻止不匹配配置执行。

持久化采用同目录临时文件、完成写入后原子替换；失败保留原文件。限制文件大小及航点数量。未知版本拒绝或明确迁移；未知字段按文档策略处理，禁止悄然丢弃关键配置。保存到不同路径即使内容相同也应写入；目标文件被外部修改时不能仅凭内存指纹跳过写入。

## 9. 标准化与幂等

先校验再标准化。拒绝 NaN、Inf、零范数或严重异常四元数；有效四元数归一化。q 与 -q 统一符号，w 接近零时采用首个非零分量为正的确定性规则。位置及姿态采用可配置量化精度；示例位置 0.001 m，最终精度须符合导航容差。

指纹包含有序航点、参考系和地图身份，不包含消息时间戳或显示名称。完整配置指纹另外包含影响导航的参数。使用固定字段顺序和确定性序列化后 SHA-256。去重基于量化值的精确定义，不采用可能不具传递性的连续容差链。

相同 Publish：仅限频提示，不更新版本、写文件、触发规划或执行。不同 Publish：校验成功才更新配置并增加版本，但也不自动规划或执行。手动重新规划即使配置不变也允许，因当前位置和地图可能变化。已完成任务允许再次显式执行，但必须满足路径有效性规则，必要时由用户重新请求规划。

规划结果记录 config_version、request_id、起始位姿和时刻；配置更新后旧结果必须丢弃。执行任务保留不可变快照，不能被新配置修改。

## 10. 状态机与并发规则

执行状态：IDLE、PLANNING、READY、EXECUTING、CANCELING、SUCCEEDED、FAILED、CANCELED。配置是否存在、是否有待处理配置作为独立属性，不用一个枚举混合所有情况。

| 当前情况 | 事件 | 处理 |
|---|---|---|
| 无有效配置 | 规划/执行 | 拒绝，报告原因 |
| 空闲或 READY | 新有效配置 | 替换配置，使旧规划失效 |
| PLANNING | 新配置 | 请求取消旧规划或标记结果过期，保留最新请求 |
| EXECUTING | 相同配置 | 忽略，任务继续 |
| EXECUTING | 不同配置/加载 | 放入待处理配置，当前任务不切换 |
| EXECUTING | 再次执行 | 拒绝或报告已有任务，不创建第二个目标 |
| READY | 执行 | 检查环境、版本、路径有效性，发送目标 |
| EXECUTING | 取消 | 转 CANCELING，等待目标终态 |
| 任意异步阶段 | 旧回调 | 按 request_id/task_id 丢弃 |

待处理配置采用最新有效快照，并显示替换事件。任务终止后提升为当前配置，规划失效，等待下一次显式plan和execute。规划中重复plan、执行中plan按统一状态转换规则处理，不能创建并发冲突目标。取消超时进入结果未知的受限状态，不将任务假定已停止，也不允许立即发送新目标。关闭节点时尝试有界取消，但独立底盘安全机制必须负责失联保护。

## 11. 路径生成与执行规则

规划从机器人当前 map 位姿出发，目标为有序航点。仅允许通过真实 TF 转换改变参考系；不能改 frame_id 代替坐标转换。补齐时间戳使用 ROS 时钟，保持 use_sim_time 一致。

规划返回后检查非空、数值、参考系、起点衔接、终点合理性；机器人足迹与障碍物检查优先复用 Nav2 已有能力。平滑为可选步骤，必须检查平滑后路径仍有效且是否偏离要求经过的航点。

执行几何与规划年龄分开管理：保留原规划时刻、配置版本和快照用于有效性判断；发送给Humble FollowPath的执行拷贝中，各Pose时间戳使用0（最新TF）使map几何按当前定位转换到局部参考系，不能用规划时历史TF锁定odom目标。原Path、预览和规划年龄不得被清零或刷新以绕过过期检查；执行前仍须确认当前TF可用。

执行前检查配置版本、规划年龄和起点位移；超过阈值拒绝执行并要求重新规划。地图变化监测可使路径失效，地图时间戳本身不构成碰撞有效性证明。对于无法验证的动态环境，明确显示验证限制。

执行中根据map定位位姿按配置顺序记录每个中途航点的实际进入范围事件；未确认经过的点不得因Action成功而自动补记。终点另验位置和朝向。允许控制器在障碍附近绕行，但漏点或无法通过均为任务失败；需要取消未结束的Action时应报告取消请求、终态和停车观测。第一版不自动重新规划、不跳点继续。

脚本不直接发布 cmd_vel。运行前确保没有其他导航入口同时下发任务；检查其他任务的能力取决于具体部署，不能只凭本节点状态推断全系统空闲。第一版规定使用期间不同时操作 Nav2 Goal/其他导航客户端；后续可增加统一任务仲裁。

## 12. 终端显示与事件报告

统一格式：`[时间][级别][任务ID][阶段] 内容`。关键事件立即输出，进度默认每秒最多一次，重复消息限频。时间区分人可读系统时间与 ROS 时间，任务耗时采用单调时钟或明确的仿真时间口径。

必须报告：配置来源及数量、起始位姿、航点清单、规划耗时与路径长度、目标接受状态、进度、经过航点事件、取消、终态、错误码和原始信息。

航点经过判定按当前任务有序推进，使用 map 位姿、距离阈值、滞回和一次性事件；初始就在航点范围内也应有明确规则。未进入范围的点不能直接标为已到达；绕行跳过时报告未确认。重复或重叠航点应提示。定位不可靠时暂停几何判定。

剩余距离优先使用版本支持的反馈；自行计算时标记为估算，沿路径投影并约束进度，不能用到终点直线距离冒充剩余路径距离。

障碍处理只报告有依据的事件。仅凭速度为零不能认定遇到障碍，控制器报错也不能必然归因于障碍。额外代价地图监测若未实现，显示“原因未确认”及原始错误。第一版不输出虚构的“正在绕障”或“自动重规划”。

```text
[10:20:00][INFO][任务12][配置] 收到2个航点，版本3
[10:20:01][INFO][任务12][规划] 完成，长度7.2m，耗时0.8s
[10:20:03][INFO][任务12][导航] 目标已接受
[10:20:08][INFO][任务12][进度] 前往航点1/2，距离1.6m（估算）
[10:20:12][INFO][任务12][航点] 进入航点1位置范围，未要求停车
[10:20:18][ERROR][任务12][失败] 控制器错误：无法生成有效控制，障碍原因未确认
```

## 13. 参数设计

参数集中在 navigator.yaml，包括 input_topic、preview_topic、frame_id、base_frame、use_sim_time、各 Action 名、插件 ID、config_file、map_identity、最大航点数、文件大小限制、去重量化精度、航点经过阈值、路径最大年龄、起点偏移阈值、TF/服务器/规划/响应/取消超时、日志频率。

第一版 auto_execute 固定关闭；若后续开放默认仍为 false。影响任务语义的参数执行中不得直接修改当前任务，应拒绝或作为下一任务配置。导航容差、超时和速度约束在仿真测试后确定，不把示例数字当作验收基线。

## 14. 安全与可靠性

取消请求不等于机器人已停止；必须分别报告 Action 取消终态和独立观测的速度状态。实体急停、底盘看门狗及速度安全链独立于本脚本。实体上电、运动和硬件测试需要用户当次明确授权，不能由本说明书替代。

失联时显示控制状态未知，禁止无限重试或自动重新启动。恢复连接及节点重启不自动恢复运动。保存加载失败不破坏有效内存配置。配置与路径均不可被回调原地修改。仿真时钟暂停、跳变和 TF 失效须有明确错误处理。

## 15. 测试计划与验收

| 测试层级 | 场景 | 预期 |
|---|---|---|
| 单元 | 无效数值、四元数、空路径、参考系 | 拒绝无效输入，原配置保留 |
| 单元 | 时间戳变化、q/-q、微小误差、顺序变化 | 前三者按规则去重，顺序变化视为新配置 |
| 单元 | YAML round-trip、损坏文件、未知版本、写入中断 | 数据一致，错误可报告，原文件保留 |
| 状态测试 | 新配置覆盖规划、迟到回调、重复执行 | 旧结果不能进入 READY 或触发运动 |
| 集成 | Action 拒绝、超时、取消失败、服务器失联 | 状态准确，无自动重启任务 |
| 仿真 | 开放区两点、三点转弯、墙体绕行 | 顺序合理，终点满足目标检查器容差 |
| 仿真 | 不可达航点、起点移动、旧路径 | 不启动不适用路径，提示重新规划 |
| 仿真 | 中途取消、执行中发布与加载 | 当前任务一致，新配置不自动接管 |
| 仿真 | 新障碍、定位失效、时钟异常、节点重启 | 明确失败或未知状态，无未经请求运动 |
| 显示测试 | 经过航点、暂停、失败原因 | 事件不重复，估算有标记，原因有证据 |

记录 ROS/Nav2 版本、配置指纹、地图身份、任务 ID、日志和必要 rosbag。量化指标包括规划耗时、到达误差、取消响应时间和进度误差；阈值在实施前依据实际配置冻结。每项用例记录通过/失败及证据，不能仅以界面显示正常验收。

第一版最低验收：首次Publish、相同Publish和加载均不自动规划或运动；只有用户请求plan才规划，只有用户请求execute才运动；规划失败不运动；按序实际经过全部中途航点并满足终点位置/朝向才报告成功；遇障无法通过则失败，不自动重规划或跳点；取消有终态报告；新配置不覆盖运行任务；文件可可靠往返；旧回调无法触发执行；成功失败均有可追溯日志。

## 16. 开发顺序与交付物

1. R00-A资源调研 → R00-B候选实测 → R00-C复用决策与设计/范围冻结。
2. U01正式环境基线与验收指标；基础故障先处理，通过后进入U02。
3. U02包与外部接口骨架。
4. U03数据模型/校验/去重 → U04持久化与U05任务协调，按依赖验收。
5. U06受用户请求的异步规划 → U07路径预览与执行前有效性。
6. U08官方FollowPath执行 → U09取消与故障处理；U08/U09后完成U10报告和实际经过判定。
7. U11综合回归 → U12独立复现、交付文档和归档。

交付物：ROS Python 包、启动与参数文件、YAML 示例、RViz2 显示说明、测试与证据、用户操作说明。项目实现进入现有 ROS 工作空间并按该工作空间的 Git、测试和归档规则管理。本文件按用户指定目录交付，仅为说明书，不代表代码实施或里程碑验收完成。

## 17. 后续扩展

自动重新规划应有触发依据、频率限制、次数限制和失败终止策略；先取消或协调旧任务，再启动新路径。RViz2 面板复用现有服务接口。逐点任务通过独立任务层扩展。公共接口稳定、存储 schema 有版本、Nav2 差异收敛在适配模块，避免在各模块散布版本判断。

## 18. 官方参考

- [ComputePathThroughPoses](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/bt_plugins/actions/ComputePathThroughPoses/)
- [Nav2 Simple Commander](https://docs.nav2.org/rolling/configuration_and_development/simple_commander_api/simple_commander_api/)
- [Nav2 Navigation Servers](https://docs.nav2.org/rolling/getting_started/navigation_concepts/navigation_servers/)
- [Navigate Through Poses 行为树](https://docs.nav2.org/jazzy/getting_started/nav2_behavior_trees/trees/nav_through_poses_recovery/)

参考页面用于架构解释；开发时以本机 ROS/Nav2 接口及对应版本文档为准。

## 19. R00-C选型与实施边界（v1.2）

- 复用ROS2 Humble/Nav2 1.1.20的官方规划和执行Action、现有Waypoint Plugin输入、rclpy/TF及已有安全速度链。来源、包版本、许可证和文件SHA256见R00-A/B证据与R00-C复用决策记录；上游固定源码提交不能替代本机二进制身份。
- 路线A已完成本单元真实RViz两点最小闭环及运动取消复验；Simple Commander、mapoi不作为本次生产入口/依赖。仍不表示完整应用已实现。
- U02–U10保留或改为复用＋薄适配，任务协调、YAML、指纹、路径有效性和实际航点结果是明确开发缺口；不重写规划器/控制器或编辑器，不取消对应集成验收。
- 当前RPP与评估profile仅提供已测环境证据，不能视为通用生产默认。反向终点朝向/进展及绕墙失败列入U01基础FollowPath关口；控制参数和正式指标由U01确认。若修复要求更换选定组件或接口，回到R00-C修订，不以降低需求或跳过测试解决。
- 任务成功必须同时满足Nav2终态、按序实际经过与新鲜map终点姿态/停止证据。外部服务接受、API成功或一次最小闭环不能代替U08–U12完整验收。
