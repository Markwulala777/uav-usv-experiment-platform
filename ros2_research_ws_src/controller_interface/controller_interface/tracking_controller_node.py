import copy

import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import ControllerCommand, ControllerReference


class TrackingControllerNode(Node):
    def __init__(self):
        super().__init__("tracking_controller")

        self.reference = None

        self.command_pub = self.create_publisher(ControllerCommand, "/controller/command", 10)

        self.create_subscription(
            ControllerReference, "/controller/reference_filtered", self.reference_cb, 10
        )

        self.timer = self.create_timer(0.05, self.publish_command)
        self.get_logger().info("controller_interface tracking controller is running.")

    def reference_cb(self, msg):
        self.reference = msg

    def publish_command(self):
        if self.reference is None:
            return

        msg = ControllerCommand()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.control_mode = ControllerCommand.MODE_POSITION
        msg.position_setpoint = copy.deepcopy(self.reference.target_pose)
        msg.source = self.reference.source
        self.command_pub.publish(msg)


def main():
    rclpy.init()
    node = TrackingControllerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
