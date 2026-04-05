#!/usr/bin/env bash

resolve_ros1_world_profile() {
  local install_root="$1"
  local scenario_id="$2"

  SCENARIO_WORLD_LAUNCH_FILE=""
  SCENARIO_WORLD_FILE=""

  case "$scenario_id" in
    scenario_1_static_ground_qr)
      SCENARIO_WORLD_LAUNCH_FILE="$install_root/XTDrone/sitl_config/launch/zhihang1.launch"
      SCENARIO_WORLD_FILE="$install_root/XTDrone/sitl_config/worlds/zhihang1.world"
      ;;
    scenario_2_ground_moving_qr)
      SCENARIO_WORLD_LAUNCH_FILE="$install_root/XTDrone/sitl_config/launch/outdoor2_precision_landing.launch"
      SCENARIO_WORLD_FILE="$install_root/XTDrone/sitl_config/worlds/outdoor2.world"
      ;;
    scenario_3_maritime_usv_qr)
      SCENARIO_WORLD_LAUNCH_FILE="$install_root/PX4_Firmware/launch/sandisland.launch"
      SCENARIO_WORLD_FILE="$install_root/catkin_ws/build/vrx_gazebo/worlds/example_course.world"
      ;;
    *)
      echo "Unsupported ROS1 world scenario: $scenario_id" >&2
      return 1
      ;;
  esac
}

