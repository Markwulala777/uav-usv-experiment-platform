import math

import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import RelativeState, TouchdownEvent, TouchdownState


class ContactMonitorNode(Node):
    def __init__(self):
        super().__init__("contact_monitor")

        self.relative_state = None
        self.current_state = TouchdownState.NO_CONTACT
        self.landing_completed = False
        self.landing_failed = False
        self.first_contact_time = None

        self.declare_parameter("contact_height_threshold", 0.15)
        self.declare_parameter("stable_contact_duration", 0.5)
        self.declare_parameter("success_xy_threshold", 0.5)
        self.declare_parameter("success_vertical_speed", 0.8)
        self.declare_parameter("success_lateral_speed", 0.8)

        self.state_pub = self.create_publisher(TouchdownState, "/touchdown/state", 10)
        self.event_pub = self.create_publisher(TouchdownEvent, "/touchdown/event", 10)

        self.create_subscription(RelativeState, "/relative_state/active", self.relative_state_cb, 10)
        self.timer = self.create_timer(0.05, self.evaluate)
        self.get_logger().info("touchdown_manager contact monitor is running.")

    def relative_state_cb(self, msg):
        self.relative_state = msg

    def publish_event(self, event_type, reason):
        msg = TouchdownEvent()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.event_type = event_type
        msg.reason = reason
        self.event_pub.publish(msg)

    def publish_state(self, reason):
        msg = TouchdownState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.contact_state = self.current_state
        msg.landing_completed = self.landing_completed
        msg.landing_failed = self.landing_failed
        msg.reason = reason
        self.state_pub.publish(msg)

    def evaluate(self):
        if self.relative_state is None:
            return

        contact_height_threshold = float(self.get_parameter("contact_height_threshold").value)
        stable_contact_duration = float(self.get_parameter("stable_contact_duration").value)
        success_xy_threshold = float(self.get_parameter("success_xy_threshold").value)
        success_vertical_speed = float(self.get_parameter("success_vertical_speed").value)
        success_lateral_speed = float(self.get_parameter("success_lateral_speed").value)

        x = self.relative_state.position.x
        y = self.relative_state.position.y
        z = self.relative_state.position.z
        lateral_error = math.hypot(x, y)
        lateral_speed = math.hypot(
            self.relative_state.linear_velocity.x, self.relative_state.linear_velocity.y
        )
        vertical_speed = abs(self.relative_state.linear_velocity.z)
        now_ns = self.get_clock().now().nanoseconds

        reason = "no_contact"

        if self.landing_completed:
            self.current_state = TouchdownState.STABLE_CONTACT
            reason = "landing_completed"
            self.publish_state(reason)
            return

        if z > contact_height_threshold:
            if self.current_state in (TouchdownState.FIRST_CONTACT, TouchdownState.STABLE_CONTACT):
                self.current_state = TouchdownState.CONTACT_LOST
                self.landing_failed = True
                reason = "contact_lost"
                self.publish_event("contact_lost", reason)
            else:
                self.current_state = TouchdownState.NO_CONTACT
            self.first_contact_time = None
            self.publish_state(reason)
            return

        if self.current_state == TouchdownState.NO_CONTACT:
            self.current_state = TouchdownState.FIRST_CONTACT
            self.first_contact_time = now_ns
            reason = "first_contact"
            self.publish_event("first_contact", reason)
            self.publish_state(reason)
            return

        if self.current_state == TouchdownState.FIRST_CONTACT and self.first_contact_time is not None:
            contact_time_s = (now_ns - self.first_contact_time) / 1e9
            stable = (
                contact_time_s >= stable_contact_duration
                and lateral_error <= success_xy_threshold
                and lateral_speed <= success_lateral_speed
                and vertical_speed <= success_vertical_speed
            )
            if stable:
                self.current_state = TouchdownState.STABLE_CONTACT
                self.landing_completed = True
                reason = "stable_contact"
                self.publish_event("stable_contact", reason)
                self.publish_event("landing_completed", reason)

        self.publish_state(reason)


def main():
    rclpy.init()
    node = ContactMonitorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
