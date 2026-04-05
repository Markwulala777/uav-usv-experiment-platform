import copy

import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import ControllerReference, SafetyStatus


class ReferenceFilterNode(Node):
    def __init__(self):
        super().__init__("reference_filter")

        self.active_reference = None
        self.last_safe_reference = None
        self.safety_status = None

        self.filtered_pub = self.create_publisher(
            ControllerReference, "/controller/reference_filtered", 10
        )

        self.create_subscription(
            ControllerReference, "/controller/reference_active", self.active_reference_cb, 10
        )
        self.create_subscription(SafetyStatus, "/safety/status", self.safety_status_cb, 10)

        self.timer = self.create_timer(0.05, self.publish_filtered)
        self.get_logger().info("safety_manager reference filter is running.")

    def active_reference_cb(self, msg):
        self.active_reference = msg
        if self.safety_status is None or not self.safety_status.abort_requested:
            self.last_safe_reference = copy.deepcopy(msg)

    def safety_status_cb(self, msg):
        self.safety_status = msg

    def publish_filtered(self):
        if self.active_reference is None:
            return

        source_msg = self.active_reference
        if (
            self.safety_status is not None
            and self.safety_status.abort_requested
            and self.last_safe_reference is not None
        ):
            source_msg = self.last_safe_reference

        msg = copy.deepcopy(source_msg)
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.source = f"{msg.source}:filtered"
        self.filtered_pub.publish(msg)


def main():
    rclpy.init()
    node = ReferenceFilterNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
