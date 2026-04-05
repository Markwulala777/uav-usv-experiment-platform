import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from mission_stack_msgs.msg import (
    LandingDecisionStatus,
    MissionStatus,
    RelativeState,
    SafetyStatus,
    TouchdownState,
)


class PhaseManagerNode(Node):
    def __init__(self):
        super().__init__("phase_manager")

        self.relative_state = None
        self.decision_status = None
        self.safety_status = None
        self.touchdown_state = None
        self.current_phase = MissionStatus.SEARCH
        self.previous_phase = MissionStatus.SEARCH
        self.transition_reason = "startup"

        self.declare_parameter("approach_xy_gate", 3.0)
        self.declare_parameter("align_xy_gate", 1.5)
        self.declare_parameter("synchronize_lateral_speed_gate", 0.8)
        self.declare_parameter("require_decision_continue", False)

        self.phase_pub = self.create_publisher(MissionStatus, "/mission/phase", 10)
        self.landing_completed_pub = self.create_publisher(Bool, "/mission/landing_completed", 10)

        self.create_subscription(RelativeState, "/relative_state/active", self.relative_state_cb, 10)
        self.create_subscription(
            LandingDecisionStatus, "/landing_decision/status", self.decision_status_cb, 10
        )
        self.create_subscription(SafetyStatus, "/safety/status", self.safety_status_cb, 10)
        self.create_subscription(TouchdownState, "/touchdown/state", self.touchdown_state_cb, 10)

        self.timer = self.create_timer(0.05, self.evaluate)
        self.get_logger().info("mission_manager phase manager is running.")

    def relative_state_cb(self, msg):
        self.relative_state = msg

    def decision_status_cb(self, msg):
        self.decision_status = msg

    def safety_status_cb(self, msg):
        self.safety_status = msg

    def touchdown_state_cb(self, msg):
        self.touchdown_state = msg

    def set_phase(self, next_phase, reason):
        if next_phase == self.current_phase:
            self.transition_reason = reason
            return

        self.previous_phase = self.current_phase
        self.current_phase = next_phase
        self.transition_reason = reason

    def evaluate(self):
        if self.safety_status is not None and self.safety_status.abort_requested:
            self.set_phase(MissionStatus.ABORT_GO_AROUND, self.safety_status.reason or "safety_abort")
        elif (
            self.decision_status is not None
            and self.decision_status.advisory in (LandingDecisionStatus.ABORT, LandingDecisionStatus.GO_AROUND)
        ):
            reason = ",".join(self.decision_status.reason_codes) or "decision_abort"
            self.set_phase(MissionStatus.ABORT_GO_AROUND, reason)
        elif self.touchdown_state is not None and self.touchdown_state.landing_completed:
            self.set_phase(MissionStatus.POST_LANDING, self.touchdown_state.reason or "landing_completed")
        elif (
            self.touchdown_state is not None
            and self.touchdown_state.contact_state in (TouchdownState.FIRST_CONTACT, TouchdownState.STABLE_CONTACT)
        ):
            self.set_phase(MissionStatus.TOUCHDOWN, self.touchdown_state.reason or "touchdown_contact")
        elif self.relative_state is None:
            self.set_phase(MissionStatus.SEARCH, "waiting_for_relative_state")
        else:
            approach_xy_gate = float(self.get_parameter("approach_xy_gate").value)
            align_xy_gate = float(self.get_parameter("align_xy_gate").value)
            sync_lateral_speed_gate = float(self.get_parameter("synchronize_lateral_speed_gate").value)
            require_decision_continue = bool(
                self.get_parameter("require_decision_continue").value
            )
            xy_error = math.hypot(self.relative_state.position.x, self.relative_state.position.y)
            lateral_speed = math.hypot(
                self.relative_state.linear_velocity.x, self.relative_state.linear_velocity.y
            )

            if xy_error > approach_xy_gate:
                self.set_phase(MissionStatus.APPROACH, "outside_approach_gate")
            elif xy_error > align_xy_gate:
                self.set_phase(MissionStatus.ALIGN, "inside_approach_gate")
            elif lateral_speed > sync_lateral_speed_gate:
                self.set_phase(MissionStatus.SYNCHRONIZE, "align_complete_sync_pending")
            elif require_decision_continue:
                if (
                    self.decision_status is not None
                    and self.decision_status.advisory == LandingDecisionStatus.CONTINUE
                ):
                    self.set_phase(MissionStatus.TERMINAL_DESCENT, "decision_continue")
                else:
                    self.set_phase(MissionStatus.WINDOW_WAIT, "waiting_for_window")
            else:
                self.set_phase(MissionStatus.TERMINAL_DESCENT, "decision_bypass_enabled")

        msg = MissionStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.phase = self.current_phase
        msg.previous_phase = self.previous_phase
        msg.transition_reason = self.transition_reason
        self.phase_pub.publish(msg)
        self.landing_completed_pub.publish(
            Bool(data=self.current_phase == MissionStatus.POST_LANDING)
        )


def main():
    rclpy.init()
    node = PhaseManagerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
