std_msgs/Header header
# zone_pose defines the landing-zone frame and orientation.
geometry_msgs/Pose zone_pose
# center_pose is the default terminal reference center for touchdown alignment.
geometry_msgs/Pose center_pose
geometry_msgs/Twist twist
geometry_msgs/Polygon boundary
float32 length
float32 width
float32 corridor_yaw
string source
