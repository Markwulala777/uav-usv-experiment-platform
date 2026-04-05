import math

from geometry_msgs.msg import Point32, PoseStamped, TwistStamped
import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import LandingZoneState


def yaw_from_quaternion(quaternion):
    siny_cosp = 2.0 * (
        quaternion.w * quaternion.z + quaternion.x * quaternion.y
    )
    cosy_cosp = 1.0 - 2.0 * (
        quaternion.y * quaternion.y + quaternion.z * quaternion.z
    )
    return math.atan2(siny_cosp, cosy_cosp)


class PlatformLandingZoneStateNode(Node):
    def __init__(self):
        super().__init__("platform_landing_zone_state")

        self.target_pose = None
        self.target_twist = None

        self.declare_parameter("deck_length", 2.0)
        self.declare_parameter("deck_width", 1.2)
        self.declare_parameter("landing_target_x", 0.5)
        self.declare_parameter("landing_target_y", 0.0)
        self.declare_parameter("landing_target_z", 0.0)
        self.declare_parameter("zone_source", "ros1_bridge_truth")

        self.zone_state_pub = self.create_publisher(LandingZoneState, "/platform/landing_zone_state", 10)
        self.legacy_zone_state_pub = self.create_publisher(LandingZoneState, "/deck/landing_zone_state", 10)
        self.target_pose_debug_pub = self.create_publisher(
            PoseStamped, "/platform_interface/truth/landing_target_pose", 10
        )
        self.target_twist_debug_pub = self.create_publisher(
            TwistStamped, "/platform_interface/truth/landing_target_twist", 10
        )

        self.create_subscription(PoseStamped, "/bridge/landing_target/truth/pose", self.target_pose_cb, 10)
        self.create_subscription(TwistStamped, "/bridge/landing_target/truth/twist", self.target_twist_cb, 10)
        self.timer = self.create_timer(0.05, self.publish_outputs)
        self.get_logger().info("platform_interface landing-zone state publisher is running.")

    def target_pose_cb(self, msg):
        self.target_pose = msg
        self.target_pose_debug_pub.publish(msg)

    def target_twist_cb(self, msg):
        self.target_twist = msg
        self.target_twist_debug_pub.publish(msg)

    def publish_outputs(self):
        if self.target_pose is None or self.target_twist is None:
            return

        deck_length = float(self.get_parameter("deck_length").value)
        deck_width = float(self.get_parameter("deck_width").value)
        corridor_yaw = yaw_from_quaternion(self.target_pose.pose.orientation)
        half_length = deck_length / 2.0
        half_width = deck_width / 2.0

        msg = LandingZoneState()
        msg.header = self.target_pose.header
        msg.zone_pose = self.target_pose.pose
        msg.center_pose = self.target_pose.pose
        msg.twist = self.target_twist.twist
        msg.length = deck_length
        msg.width = deck_width
        msg.corridor_yaw = corridor_yaw
        msg.source = str(self.get_parameter("zone_source").value)
        msg.boundary.points = [
            Point32(x=half_length, y=half_width, z=0.0),
            Point32(x=half_length, y=-half_width, z=0.0),
            Point32(x=-half_length, y=-half_width, z=0.0),
            Point32(x=-half_length, y=half_width, z=0.0),
        ]
        self.zone_state_pub.publish(msg)
        self.legacy_zone_state_pub.publish(msg)


def main():
    rclpy.init()
    node = PlatformLandingZoneStateNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
