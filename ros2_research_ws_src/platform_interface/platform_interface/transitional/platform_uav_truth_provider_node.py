import rclpy
from geometry_msgs.msg import PoseStamped, TwistStamped
from rclpy.node import Node
from mission_stack_msgs.msg import UavState


class PlatformUavTruthProviderNode(Node):
    def __init__(self):
        super().__init__("platform_uav_truth_provider")

        self.uav_pose = None
        self.uav_twist = None

        self.declare_parameter("uav_source", "ros1_bridge_truth")

        self.uav_state_pub = self.create_publisher(UavState, "/uav/state_truth", 10)
        self.uav_pose_debug_pub = self.create_publisher(PoseStamped, "/platform_interface/truth/uav_pose", 10)
        self.uav_twist_debug_pub = self.create_publisher(TwistStamped, "/platform_interface/truth/uav_twist", 10)

        self.create_subscription(PoseStamped, "/bridge/uav/truth/pose", self.uav_pose_cb, 10)
        self.create_subscription(TwistStamped, "/bridge/uav/truth/twist", self.uav_twist_cb, 10)
        self.timer = self.create_timer(0.05, self.publish_outputs)
        self.get_logger().info(
            "platform_interface transitional UAV truth provider is running. "
            "This node is migration-only and not the long-term /uav owner."
        )

    def uav_pose_cb(self, msg):
        self.uav_pose = msg
        self.uav_pose_debug_pub.publish(msg)

    def uav_twist_cb(self, msg):
        self.uav_twist = msg
        self.uav_twist_debug_pub.publish(msg)

    def publish_outputs(self):
        if self.uav_pose is None or self.uav_twist is None:
            return

        msg = UavState()
        msg.header = self.uav_pose.header
        msg.pose = self.uav_pose.pose
        msg.twist = self.uav_twist.twist
        msg.source = str(self.get_parameter("uav_source").value)
        self.uav_state_pub.publish(msg)


def main():
    rclpy.init()
    node = PlatformUavTruthProviderNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
