import math

import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import LandingWindowStatus, MissionStatus, RelativeState


class WindowStatusNode(Node):
    def __init__(self):
        super().__init__("window_status")

        self.relative_state = None
        self.mission_status = None

        self.declare_parameter("window_xy_gate", 0.75)
        self.declare_parameter("window_lateral_speed_gate", 0.8)
        self.declare_parameter("window_vertical_speed_gate", 0.8)

        self.window_pub = self.create_publisher(LandingWindowStatus, "/landing_window/status", 10)

        self.create_subscription(RelativeState, "/relative_state/active", self.relative_state_cb, 10)
        self.create_subscription(MissionStatus, "/mission/phase", self.mission_status_cb, 10)

        self.timer = self.create_timer(0.05, self.evaluate)
        self.get_logger().info("landing_decision window status node is running.")

    def relative_state_cb(self, msg):
        self.relative_state = msg

    def mission_status_cb(self, msg):
        self.mission_status = msg

    def evaluate(self):
        if self.relative_state is None:
            return

        xy_gate = float(self.get_parameter("window_xy_gate").value)
        lateral_speed_gate = float(self.get_parameter("window_lateral_speed_gate").value)
        vertical_speed_gate = float(self.get_parameter("window_vertical_speed_gate").value)

        xy_error = math.hypot(self.relative_state.position.x, self.relative_state.position.y)
        lateral_speed = math.hypot(
            self.relative_state.linear_velocity.x, self.relative_state.linear_velocity.y
        )
        vertical_speed = abs(self.relative_state.linear_velocity.z)
        phase = self.mission_status.phase if self.mission_status is not None else MissionStatus.SEARCH

        phase_ready = phase in (
            MissionStatus.SYNCHRONIZE,
            MissionStatus.WINDOW_WAIT,
            MissionStatus.TERMINAL_DESCENT,
        )
        window_open = (
            phase_ready
            and xy_error <= xy_gate
            and lateral_speed <= lateral_speed_gate
            and vertical_speed <= vertical_speed_gate
        )
        score = max(
            0.0,
            1.0
            - 0.4 * min(1.0, xy_error / max(xy_gate, 1e-6))
            - 0.3 * min(1.0, lateral_speed / max(lateral_speed_gate, 1e-6))
            - 0.3 * min(1.0, vertical_speed / max(vertical_speed_gate, 1e-6)),
        )

        reason = "window_open" if window_open else "window_closed"
        if not phase_ready:
            reason = "phase_not_ready"
        elif xy_error > xy_gate:
            reason = "xy_error_too_large"
        elif lateral_speed > lateral_speed_gate:
            reason = "lateral_speed_too_large"
        elif vertical_speed > vertical_speed_gate:
            reason = "vertical_speed_too_large"

        msg = LandingWindowStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.window_open = window_open
        msg.window_score = float(score)
        msg.window_reason = reason
        self.window_pub.publish(msg)


def main():
    rclpy.init()
    node = WindowStatusNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
