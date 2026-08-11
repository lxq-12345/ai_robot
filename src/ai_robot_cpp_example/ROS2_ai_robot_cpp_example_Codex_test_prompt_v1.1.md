# ROS 2 `ai_robot_cpp_example` 改造与测试任务 Prompt

**版本**：1.1  
**修订来源**：原始 Prompt v1.0  
**文件性质**：正式执行 Prompt  
**工作空间**：`/home/ubuntu/ai_robot_ws`  
**目标 package**：`ai_robot_cpp_example`

请在本地工作空间中完成以下任务。先检查现有文件和工作区状态，再做增量修改；不得覆盖或撤销与本任务无关的已有改动。

## 一、任务目标

把当前最小 ROS 2 C++ 节点重构为可复用、可实例化、可自动测试的 `BaselineNode`，并增加 `/robot_status` Topic 发布及对应的自动化测试。

必须保留现有 `status_formatter.hpp` 和 `test_status_formatter.cpp` 的功能，已有测试仍须通过。

## 二、先检查当前实现

修改前至少读取并确认以下文件的实际内容：

- `src/ai_robot_cpp_example/src/baseline_node.cpp`
- `src/ai_robot_cpp_example/include/ai_robot_cpp_example/status_formatter.hpp`
- `src/ai_robot_cpp_example/test/test_status_formatter.cpp`
- `src/ai_robot_cpp_example/CMakeLists.txt`
- `src/ai_robot_cpp_example/package.xml`

如果实际结构与本 Prompt 描述不同，应以工作区中的现有文件为基础完成同一目标，并在最终报告中说明差异。

## 三、重构节点结构

采用以下职责划分：

```text
include/ai_robot_cpp_example/baseline_node.hpp  # BaselineNode 类声明
src/baseline_node.cpp                           # BaselineNode 类实现
src/baseline_main.cpp                           # 仅包含程序入口 main()
```

在命名空间 `ai_robot_cpp_example` 中定义：

```cpp
class BaselineNode : public rclcpp::Node
```

具体要求：

1. 节点名称固定为 `baseline_cpp_node`。
2. `BaselineNode` 构造函数中继续调用现有的 `status_line("ready")` 生成启动日志，不修改 `status_formatter.hpp` 的既有语义。
3. 按当前 formatter 的实现，启动日志内容应为 `ai_robot_cpp_example:ready`。
4. `main()` 仅负责：
   - 调用 `rclcpp::init()`；
   - 创建 `BaselineNode`；
   - 调用 `rclcpp::spin()`；
   - 调用 `rclcpp::shutdown()`；
   - 正常返回。

不要把 `BaselineNode` 的实现重新放回 `main()`，也不要把完整实现写成 header-only 代码。

## 四、增加 Topic 通信

在 `BaselineNode` 类中创建 publisher：

- Topic：`/robot_status`
- 消息类型：`std_msgs/msg/String`
- 消息内容：`ready`

节点启动时发布一条状态消息。为保证晚于节点启动的 subscriber 仍能可靠取得最后一条状态，publisher 必须使用：

```cpp
rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local()
```

publisher 必须保存为 `BaselineNode` 的成员，发布逻辑必须属于该类。这里的 Topic 载荷是 `ready`，与经过 formatter 生成的启动日志 `ai_robot_cpp_example:ready` 不同。

## 五、增加 Node 自动测试

新增：

```text
test/test_baseline_node.cpp
```

使用 `ament_cmake_gtest` 实现以下测试：

1. **节点创建测试**：`std::make_shared<ai_robot_cpp_example::BaselineNode>()` 成功且不抛出异常。
2. **节点名称测试**：`node->get_name()` 等于 `baseline_cpp_node`。
3. **Topic 通信测试**：测试 subscriber 订阅 `/robot_status`，并收到内容为 `ready` 的 `std_msgs/msg/String` 消息。

测试必须满足以下约束：

- 在测试 fixture 或测试环境中正确管理 `rclcpp::init()` 和 `rclcpp::shutdown()`，避免重复初始化或提前关闭 ROS context。
- Topic 测试中的 subscriber 使用与 publisher 兼容的 reliable、transient-local QoS。
- 使用 executor 驱动被测节点和测试 subscriber。
- 等待消息必须设置有限超时，建议不超过 3 秒；超时后测试明确失败，不得无限等待。
- 不依赖人工运行节点、`ros2 topic echo` 或其他人工命令。
- 每个测试应可独立判断失败原因，且不能影响现有 `test_status_formatter`。

## 六、修改构建配置

更新 `CMakeLists.txt`，至少完成以下事项：

1. 查找 `rclcpp`、`std_msgs` 和测试阶段需要的 `ament_cmake_gtest`。
2. 将 `src/baseline_node.cpp` 编译为可被节点程序和测试共同链接的库，例如 `baseline_node_lib`。
3. 将 `src/baseline_main.cpp` 编译为 `baseline_node` 可执行程序，并链接上述库。
4. 使用 `ament_target_dependencies()` 为需要的目标声明 `rclcpp` 和 `std_msgs` 依赖。
5. 在 `if(BUILD_TESTING)` 中通过 `ament_add_gtest()` 添加 `test_baseline_node.cpp`，并将测试目标链接到节点库。
6. 保留现有 `test_status_formatter` 测试。
7. 安装 `baseline_node` 可执行程序、节点库和 `include/` 下的公共 header，使构建树和安装树中的 include 路径均正确。

不要把 `ament_cmake_gtest` 当作普通运行时库链接；它用于创建和配置 GTest 测试目标。

## 七、修改 package 依赖

检查 `package.xml`，保留：

```xml
<depend>rclcpp</depend>
<test_depend>ament_cmake_gtest</test_depend>
```

如果尚未存在，增加：

```xml
<depend>std_msgs</depend>
```

不要添加本任务不需要的依赖。

## 八、执行验证

在工作空间中依次执行：

```bash
cd /home/ubuntu/ai_robot_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select ai_robot_cpp_example
source install/setup.bash
colcon test --packages-select ai_robot_cpp_example
colcon test-result --verbose
```

验收标准：

- `colcon build` 返回成功；
- `colcon test` 返回成功；
- `colcon test-result --verbose` 显示零失败；
- 原有 formatter 测试继续通过；
- Node 创建、节点名称和 Topic 通信三个新增测试全部通过。

如果某项验证失败，应定位原因并在任务范围内修复后重新验证。不得只根据命令退出码推测某个测试通过，必须以实际测试结果为依据。

## 九、最终报告

完成后报告：

1. 所有新增和修改的文件。
2. 每个文件的主要变化。
3. `colcon build` 的实际结果。
4. `colcon test` 和 `colcon test-result --verbose` 的实际结果。
5. 分别列出以下测试的 PASS/FAIL：
   - 原有 formatter 测试；
   - Node 创建测试；
   - Node 名称测试；
   - Topic 通信测试。
6. 仍存在的限制、警告或未完成事项；没有则明确说明没有。

## 十、边界与安全要求

1. 只对 `ai_robot_cpp_example` 做完成本任务所需的增量修改，不重新设计整个 package。
2. 保留现有 package 名称、节点名称和原有 formatter 行为。
3. 不修改其他 ROS 2 package，不清理整个工作空间，也不撤销用户已有改动。
4. 本任务只涉及本地构建和自动测试，不连接、不启动、不控制实体机器人，也不发布任何运动控制命令。
5. 如果现有结构造成无法满足测试要求，应先在报告中说明原因，再进行最小且必要的结构调整。
