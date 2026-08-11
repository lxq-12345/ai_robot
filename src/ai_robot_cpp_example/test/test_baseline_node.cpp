#include <chrono>
#include <memory>
#include <string>
#include <thread>

#include <gtest/gtest.h>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

#include "ai_robot_cpp_example/baseline_node.hpp"

using namespace std::chrono_literals;

class BaselineNodeTest : public testing::Test
{
protected:
  static void SetUpTestSuite()
  {
    if (!rclcpp::ok()) {
      int argc = 0;
      char ** argv = nullptr;
      rclcpp::init(argc, argv);
    }
  }

  static void TearDownTestSuite()
  {
    if (rclcpp::ok()) {
      rclcpp::shutdown();
    }
  }
};

TEST_F(BaselineNodeTest, CreatesNode)
{
  std::shared_ptr<ai_robot_cpp_example::BaselineNode> node;
  EXPECT_NO_THROW(node = std::make_shared<ai_robot_cpp_example::BaselineNode>());
  EXPECT_NE(node, nullptr);
}

TEST_F(BaselineNodeTest, UsesExpectedName)
{
  const auto node = std::make_shared<ai_robot_cpp_example::BaselineNode>();
  EXPECT_STREQ(node->get_name(), "baseline_cpp_node");
}

TEST_F(BaselineNodeTest, PublishesReadyStatus)
{
  const auto node = std::make_shared<ai_robot_cpp_example::BaselineNode>();
  const auto subscriber_node = std::make_shared<rclcpp::Node>("baseline_node_test_subscriber");
  const auto qos = rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local();

  bool received = false;
  std::string received_status;
  const auto subscription = subscriber_node->create_subscription<std_msgs::msg::String>(
    "/robot_status", qos,
    [&received, &received_status](const std_msgs::msg::String::SharedPtr message) {
      received_status = message->data;
      received = true;
    });

  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  executor.add_node(subscriber_node);

  const auto deadline = std::chrono::steady_clock::now() + 3s;
  while (rclcpp::ok() && !received && std::chrono::steady_clock::now() < deadline) {
    executor.spin_some();
    std::this_thread::sleep_for(10ms);
  }

  ASSERT_TRUE(received) << "Timed out waiting for /robot_status";
  EXPECT_EQ(received_status, "ready");
}
