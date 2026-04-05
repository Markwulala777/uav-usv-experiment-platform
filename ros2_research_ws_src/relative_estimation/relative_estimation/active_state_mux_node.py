import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import RelativeState


class ActiveStateMuxNode(Node):
    def __init__(self):
        super().__init__("relative_state_active_mux")

        self.truth_state = None
        self.estimate_state = None

        self.declare_parameter("source_mode", "truth")

        self.active_pub = self.create_publisher(RelativeState, "/relative_state/active", 10)

        self.create_subscription(RelativeState, "/relative_state/truth", self.truth_cb, 10)
        self.create_subscription(RelativeState, "/relative_state/estimate", self.estimate_cb, 10)
        self.timer = self.create_timer(0.05, self.publish_active)
        self.get_logger().info("relative_estimation active-state mux is running.")

    def truth_cb(self, msg):
        self.truth_state = msg

    def estimate_cb(self, msg):
        self.estimate_state = msg

    def publish_active(self):
        preferred_source = str(self.get_parameter("source_mode").value).strip().lower()
        msg = None
        if preferred_source == "estimate" and self.estimate_state is not None:
            msg = self.estimate_state
        elif self.truth_state is not None:
            msg = self.truth_state
        elif self.estimate_state is not None:
            msg = self.estimate_state

        if msg is not None:
            self.active_pub.publish(msg)


def main():
    rclpy.init()
    node = ActiveStateMuxNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
