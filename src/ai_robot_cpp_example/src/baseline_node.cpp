#include <memory>

#include "rclcpp/rclcpp.hpp"

#include "ai_robot_cpp_example/status_formatter.hpp"

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("baseline_cpp_node");
  RCLCPP_INFO(node->get_logger(), "%s", ai_robot_cpp_example::status_line("ready").c_str());
  rclcpp::spin_some(node);
  rclcpp::shutdown();
  return 0;
}
