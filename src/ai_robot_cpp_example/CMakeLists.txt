cmake_minimum_required(VERSION 3.8)
project(ai_robot_cpp_example)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

add_library(baseline_node_lib SHARED src/baseline_node.cpp)
target_include_directories(baseline_node_lib PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(baseline_node_lib rclcpp std_msgs)

add_executable(baseline_node src/baseline_main.cpp)
target_link_libraries(baseline_node baseline_node_lib)

install(TARGETS baseline_node_lib
  EXPORT export_baseline_node_lib
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
install(TARGETS baseline_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)

  ament_add_gtest(test_status_formatter test/test_status_formatter.cpp)
  target_include_directories(test_status_formatter PRIVATE include)

  ament_add_gtest(test_baseline_node test/test_baseline_node.cpp)
  target_link_libraries(test_baseline_node baseline_node_lib)
endif()

ament_export_targets(export_baseline_node_lib HAS_LIBRARY_TARGET)
ament_export_dependencies(rclcpp std_msgs)

ament_package()
