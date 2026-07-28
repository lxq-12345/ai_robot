cmake_minimum_required(VERSION 3.8)
project(ai_robot_cpp_example)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)

add_executable(baseline_node src/baseline_node.cpp)
target_include_directories(baseline_node PRIVATE include)
ament_target_dependencies(baseline_node rclcpp)

install(TARGETS baseline_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_status_formatter test/test_status_formatter.cpp)
  target_include_directories(test_status_formatter PRIVATE include)
endif()

ament_package()
