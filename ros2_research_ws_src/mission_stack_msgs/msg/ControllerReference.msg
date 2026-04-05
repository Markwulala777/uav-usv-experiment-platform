uint8 SOURCE_GUIDANCE=0
uint8 SOURCE_TRAJECTORY=1

std_msgs/Header header
uint8 source_type
uint8 phase
geometry_msgs/Pose target_pose
geometry_msgs/Twist target_twist
string terminal_spec
bool feasible
uint32 sequence_id
string source
