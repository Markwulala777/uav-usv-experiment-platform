import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from mission_stack_msgs.msg import RelativeState, SafetyStatus


class SafetyMonitorNode(Node):
    def __init__(self):
        super().__init__("safety_monitor")

        self.relative_state = None

        self.declare_parameter("abort_xy_error", 4.0)
        self.declare_parameter("abort_abs_z", 8.0)
        self.declare_parameter("abort_lateral_speed", 3.0)
        self.declare_parameter("safe_xy_gate", 0.75)
        self.declare_parameter("safe_lateral_speed_gate", 0.8)

        self.status_pub = self.create_publisher(SafetyStatus, "/safety/status", 10)
        self.abort_pub = self.create_publisher(Bool, "/safety/abort_request", 10)

        self.create_subscription(RelativeState, "/relative_state/active", self.relative_state_cb, 10)
        self.timer = self.create_timer(0.05, self.evaluate)
        self.get_logger().info("safety_manager monitor node is running.")

    def relative_state_cb(self, msg):
        self.relative_state = msg

    def evaluate(self):
        if self.relative_state is None:
            return

        x = self.relative_state.position.x
        y = self.relative_state.position.y
        z = self.relative_state.position.z
        lateral_speed = math.hypot(
            self.relative_state.linear_velocity.x, self.relative_state.linear_velocity.y
        )
        xy_error = math.hypot(x, y)

        abort_xy_error = float(self.get_parameter("abort_xy_error").value)
        abort_abs_z = float(self.get_parameter("abort_abs_z").value)
        abort_lateral_speed = float(self.get_parameter("abort_lateral_speed").value)
        safe_xy_gate = float(self.get_parameter("safe_xy_gate").value)
        safe_lateral_speed_gate = float(self.get_parameter("safe_lateral_speed_gate").value)

        abort_requested = (
            xy_error > abort_xy_error or abs(z) > abort_abs_z or lateral_speed > abort_lateral_speed
        )
        safe = xy_error < safe_xy_gate and lateral_speed < safe_lateral_speed_gate and not abort_requested

        reason = "nominal"
        if abort_requested:
            if xy_error > abort_xy_error:
                reason = "abort_xy_error_exceeded"
            elif abs(z) > abort_abs_z:
                reason = "abort_vertical_error_exceeded"
            else:
                reason = "abort_lateral_speed_exceeded"
        elif not safe:
            reason = "safety_hold"

        msg = SafetyStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.safe = safe
        msg.abort_requested = abort_requested
        msg.reason = reason
        self.status_pub.publish(msg)
        self.abort_pub.publish(Bool(data=abort_requested))


def main():
    rclpy.init()
    node = SafetyMonitorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
