cmake_minimum_required(VERSION 3.8)
project(ai_robot_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf launch DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  set(test_ros_log_dir "${CMAKE_CURRENT_BINARY_DIR}/ros_log")
  file(MAKE_DIRECTORY "${test_ros_log_dir}")

  ament_add_pytest_test(test_xacro_urdf test/test_xacro_urdf.py)
  ament_add_pytest_test(test_model_structure test/test_model_structure.py)
  ament_add_pytest_test(test_physical_properties test/test_physical_properties.py)
  ament_add_pytest_test(test_gazebo_plugins test/test_gazebo_plugins.py)
  ament_add_pytest_test(
    test_robot_state_publisher_launch
    test/test_robot_state_publisher_launch.py
  )

  set_tests_properties(
    test_xacro_urdf
    test_model_structure
    test_physical_properties
    test_gazebo_plugins
    test_robot_state_publisher_launch
    PROPERTIES ENVIRONMENT "ROS_LOG_DIR=${test_ros_log_dir}"
  )
endif()

ament_package()
