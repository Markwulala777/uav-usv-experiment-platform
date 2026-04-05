uint8 MODE_UNSPECIFIED=0
uint8 MODE_POINT=1
uint8 MODE_SET_SUMMARY=2

std_msgs/Header header
uint8 mode
geometry_msgs/Pose target_pose
geometry_msgs/Twist target_twist
float32 touchdown_tolerance_xy
float32 touchdown_tolerance_z
float32 heading_tolerance_rad
string source
