# 测试存放与执行规范

版本：v1.0

## 1. 基本原则

测试文件按被测责任范围存放，不按开发里程碑、测试框架或执行先后存放。

- 单个项目程序包能够独立负责的测试放入该包的`test/`；
- 项目公共契约、跨包组合和整机能力测试放入工作空间根目录`tests/`；
- M编号用于需求与证据追溯，不取代测试层级；
- 不复制成熟第三方项目的内部测试，只验证本项目选用的版本、配置、接口和组合行为；
- 自动测试与手工测试分别记录，互不替代。

## 2. 目录规则

| 目录 | 内容 | 自动发现或入口 |
|---|---|---|
| `src/<package>/test/` | 单包单元、资源契约、包级Launch测试 | `colcon test --packages-select <package>` |
| `tests/contract/` | 跨包接口、根配置、资源和安全契约 | `python3 -m pytest tests/contract` |
| `tests/integration/` | 多包、ROS图、第三方组件组合和仿真子系统测试 | `launch_test <file>`或`scripts/test.sh` |
| `tests/system/` | 整机端到端、Gate和完整能力测试 | `launch_test <file>`或`scripts/test.sh` |
| `tests/helpers/` | 仅供自动测试使用的桩、假服务和公共辅助程序 | 由所属测试调用 |
| `tests/scenario/` | 手工测试步骤、前置条件、停止方法和通过标准 | 学员或测试人员按文档执行 |
| `tests/evidence/` | 手工测试模板及需要长期保留的证据 | 人工填写，不由自动测试生成结论 |

根目录不再设置`tests/unit/`和通用`tests/launch/`。单元测试必须归责任包；Launch测试根据责任范围进入包内、`integration/`或`system/`。本文件是测试存放与执行规则的统一入口，规划和教材只引用，不另行定义冲突规则。

## 3. 归属判断

按以下顺序判断测试位置：

1. 只导入一个项目包的内部模块，放该包`test/`；
2. 只检查一个包拥有的模型、Launch、配置或资源，放该包`test/`；
3. 同时检查多个包或根目录公共配置，放`tests/contract/`；
4. 启动多个节点、多个包或第三方组件组合验证一个子系统，放`tests/integration/`；
5. 覆盖完整机器人任务、端到端能力或Gate，放`tests/system/`；
6. 需要人员操作、GUI判断或现场确认，放`tests/scenario/`并在`tests/evidence/`记录。

当一个测试同时符合多个层级时，选择能够覆盖其全部前置条件的最高层级，不复制测试文件。

## 4. 成熟第三方组件

Gazebo、Gazebo ROS插件、Nav2、SLAM Toolbox、AMCL、robot_localization等成熟组件的内部实现不属于本项目测试责任，也不得把上游源码测试复制到本仓库。本项目测试以下内容：

- 版本和依赖可用；
- 参数、Topic、Action、QoS和TF符合项目契约；
- 项目Launch能够正确组合组件；
- 正常、超时、取消、数据中断和安全场景符合项目要求；
- 组件退出后没有残留进程或破坏工程基线。

只检查单包模型、资源或配置适配时放负责集成该组件的程序包`test/`；涉及多个组件组合或真实ROS图时放`tests/integration/`；形成整机任务时放`tests/system/`。例如，M2/M3使用的Gazebo插件声明由`ai_robot_description/test/`验证，仿真运行效果分别由M2/M3集成测试验证。

当前M2/M3测试位置：

- M2模型、物理属性、轮系和Gazebo底盘插件：`src/ai_robot_description/test/`；
- M2仿真入口和速度守卫：`src/ai_robot_sim/test/`；
- M2公共底盘契约与运行态运动：`tests/contract/test_s1_m2_base_contract.py`、`tests/integration/test_s1_m2_base_motion.launch.py`；
- M3激光、相机和IMU插件声明：`src/ai_robot_description/test/test_gazebo_plugins.py`；
- M3公共参数、诊断规则与运行数据：`tests/contract/test_s1_m3_sensor_contract.py`、`tests/integration/test_s1_m3_sensors.launch.py`；
- M3 GUI人工观察：`tests/scenario/S1-1-M3传感器GUI观察说明.md`，证据写入`tests/evidence/`。

## 5. 命名和追溯

- 包内测试使用`test_<对象>.<扩展名>`；包内pytest Launch测试使用`test_<对象>_launch.py`并添加`@pytest.mark.launch_test`；
- 工作空间测试使用`test_s1_m<编号>_<能力>.<扩展名>`；
- 多M共享测试在说明中列出全部关联M，不复制文件；
- 每个M的学习教材和验收记录引用实际测试路径；
- 文件迁移后必须同步统一脚本、规划、教材、场景说明和目录契约测试。

## 6. 自动测试规则

### 6.1 包级测试

包级测试必须在`package.xml`声明测试依赖，并通过CMake或ament_python/pytest注册，使以下命令能够发现和执行：

```bash
colcon test --packages-select <package>
colcon test-result --all
```

禁止依靠修改`sys.path`从根目录导入包源码来代替正式包测试注册。

### 6.2 工作空间测试

标准全量入口为：

```bash
./scripts/test.sh
```

执行顺序固定为：目录契约、包级测试、工作空间契约、跨包集成、系统测试。某层失败时立即停止，保存失败输出，不用后续通过结果掩盖前序失败。

单独调试允许使用：

```bash
python3 -m pytest tests/contract
launch_test tests/integration/<test>.launch.py
launch_test tests/system/<test>.launch.py
```

单独测试通过后仍需根据变更风险执行包级或全量回归。

### 6.3 自动测试结果

自动测试记录至少包括命令、环境、提交号、测试数量、通过/失败/跳过数量、耗时和失败日志位置。测试完成后确认ROS 2、Gazebo和Nav2相关进程已正常退出。

## 7. 手工测试规则

手工测试用于GUI、运动现象、交互体验和无法可靠自动判定的安全观察。每份场景必须写明：

- 关联M和自动测试前置条件；
- 环境、地图、初始位姿和启动命令；
- 操作步骤、预期现象和通过标准；
- 停止、急停替代和恢复方法；
- 禁止操作和实体安全边界；
- 证据路径和结论。

执行手工测试前，相关包级、契约和集成自动测试必须通过。学员或测试人员必须亲自操作；AI运行只能作为演示。未经用户当次明确授权，不得把仿真手工场景扩展为实体机器人操作。

手工证据使用`tests/evidence/test_evidence_template.md`，结论仅可记录为“通过、未通过、未执行”。未执行不能视为通过，自动测试通过不能替代手工观察。

## 8. 变更与失败处理

- 修改自有代码时至少执行责任包测试；
- 修改公共接口、配置、TF或Launch时执行相关契约和集成测试；
- 修改导航、安全或任务链时执行相关系统测试；
- 修改测试目录、注册或统一入口时执行`tests/test_workspace_layout.sh`和`./scripts/test.sh`；
- 测试失败时先记录首个失败、日志和残留进程，再修复；不得删除断言、扩大容差或跳过测试来伪造通过；
- 新测试先确定责任层级和关联M，再创建文件。
