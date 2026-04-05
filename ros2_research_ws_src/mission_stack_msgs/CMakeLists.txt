cmake_minimum_required(VERSION 3.8)
project(mission_stack_msgs)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

set(msg_files
  "msg/ControllerCommand.msg"
  "msg/ControllerReference.msg"
  "msg/DeckState.msg"
  "msg/ExperimentEvent.msg"
  "msg/ExperimentRunStatus.msg"
  "msg/GuidanceReference.msg"
  "msg/LandingDecisionStatus.msg"
  "msg/LandingWindowStatus.msg"
  "msg/LandingZoneState.msg"
  "msg/MetricsSummary.msg"
  "msg/MissionStatus.msg"
  "msg/PlannerStatus.msg"
  "msg/PlatformState.msg"
  "msg/ReferenceTrajectory.msg"
  "msg/ReferenceTrajectoryPoint.msg"
  "msg/RelativeState.msg"
  "msg/SafetyStatus.msg"
  "msg/ScenarioProfile.msg"
  "msg/TerminalTargetSpec.msg"
  "msg/TouchdownEvent.msg"
  "msg/TouchdownState.msg"
  "msg/UavState.msg"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  DEPENDENCIES builtin_interfaces geometry_msgs std_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
