import rclpy
from geometry_msgs.msg import PoseStamped, TwistStamped
from rclpy.node import Node
from mission_stack_msgs.msg import DeckState, PlatformState


class PlatformTruthIngestNode(Node):
    def __init__(self):
        super().__init__("platform_truth_ingest")

        self.deck_pose = None
        self.deck_twist = None

        self.declare_parameter("deck_source", "ros1_bridge_truth")

        self.declare_parameter("platform_type", "deck")
        self.declare_parameter("motion_mode", "truth_feed")

        self.deck_state_pub = self.create_publisher(DeckState, "/deck/state_truth", 10)
        self.platform_state_pub = self.create_publisher(PlatformState, "/platform/state", 10)
        self.deck_pose_debug_pub = self.create_publisher(PoseStamped, "/platform_interface/truth/deck_pose", 10)
        self.deck_twist_debug_pub = self.create_publisher(TwistStamped, "/platform_interface/truth/deck_twist", 10)

        self.create_subscription(PoseStamped, "/bridge/deck/truth/pose", self.deck_pose_cb, 10)
        self.create_subscription(TwistStamped, "/bridge/deck/truth/twist", self.deck_twist_cb, 10)
        self.timer = self.create_timer(0.05, self.publish_outputs)
        self.get_logger().info("platform_interface deck truth ingest is running.")

    def deck_pose_cb(self, msg):
        self.deck_pose = msg
        self.deck_pose_debug_pub.publish(msg)

    def deck_twist_cb(self, msg):
        self.deck_twist = msg
        self.deck_twist_debug_pub.publish(msg)

    def publish_outputs(self):
        if self.deck_pose is None or self.deck_twist is None:
            return

        source = str(self.get_parameter("deck_source").value)

        deck_msg = DeckState()
        deck_msg.header = self.deck_pose.header
        deck_msg.pose = self.deck_pose.pose
        deck_msg.twist = self.deck_twist.twist
        deck_msg.angular_velocity = self.deck_twist.twist.angular
        deck_msg.source = source
        self.deck_state_pub.publish(deck_msg)

        platform_msg = PlatformState()
        platform_msg.header = self.deck_pose.header
        platform_msg.pose = self.deck_pose.pose
        platform_msg.twist = self.deck_twist.twist
        platform_msg.angular_velocity = self.deck_twist.twist.angular
        platform_msg.platform_type = str(self.get_parameter("platform_type").value)
        platform_msg.motion_mode = str(self.get_parameter("motion_mode").value)
        platform_msg.source = source
        self.platform_state_pub.publish(platform_msg)


def main():
    rclpy.init()
    node = PlatformTruthIngestNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
