cmake_minimum_required(VERSION 3.0.2)
project(platform_interface_ros1)

find_package(catkin REQUIRED COMPONENTS
  gazebo_msgs
  geometry_msgs
  rospy
  std_msgs
  tf
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/platform_truth_bridge.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
)
