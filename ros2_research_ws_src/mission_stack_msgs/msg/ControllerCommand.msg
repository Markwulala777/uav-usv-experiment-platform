uint8 MODE_POSITION=0
uint8 MODE_VELOCITY=1
uint8 MODE_ACCELERATION=2
uint8 MODE_ATTITUDE=3
uint8 MODE_BODY_RATE=4

std_msgs/Header header
uint8 control_mode
geometry_msgs/Pose position_setpoint
geometry_msgs/Twist velocity_setpoint
geometry_msgs/Vector3 acceleration_setpoint
geometry_msgs/Quaternion attitude_setpoint
geometry_msgs/Vector3 body_rate_setpoint
string source
