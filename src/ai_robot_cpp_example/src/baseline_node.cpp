#include "ai_robot_cpp_example/baseline_node.hpp"
#include "ai_robot_cpp_example/status_formatter.hpp"

namespace ai_robot_cpp_example
{

BaselineNode::BaselineNode(const rclcpp::NodeOptions & options)
: Node("baseline_cpp_node", options)
{
  const auto qos = rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local();
  status_publisher_ = create_publisher<std_msgs::msg::String>("/robot_status", qos);

  std_msgs::msg::String message;
  message.data = "ready";
  status_publisher_->publish(message);

  RCLCPP_INFO(get_logger(), "%s", status_line("ready").c_str());
}

}  // namespace ai_robot_cpp_example
