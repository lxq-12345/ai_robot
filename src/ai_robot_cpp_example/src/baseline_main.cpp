#include <memory>

#include "rclcpp/rclcpp.hpp"

#include "ai_robot_cpp_example/baseline_node.hpp"

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<ai_robot_cpp_example::BaselineNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
