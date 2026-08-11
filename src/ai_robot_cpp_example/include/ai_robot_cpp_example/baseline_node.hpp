#ifndef AI_ROBOT_CPP_EXAMPLE__BASELINE_NODE_HPP_
#define AI_ROBOT_CPP_EXAMPLE__BASELINE_NODE_HPP_

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

namespace ai_robot_cpp_example
{

class BaselineNode : public rclcpp::Node
{
public:
  explicit BaselineNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_publisher_;
};

}  // namespace ai_robot_cpp_example

#endif  // AI_ROBOT_CPP_EXAMPLE__BASELINE_NODE_HPP_
