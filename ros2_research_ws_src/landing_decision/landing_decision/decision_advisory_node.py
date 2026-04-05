import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import (
    LandingDecisionStatus,
    LandingWindowStatus,
    MissionStatus,
    SafetyStatus,
)


class DecisionAdvisoryNode(Node):
    def __init__(self):
        super().__init__("decision_advisory")

        self.window_status = None
        self.mission_status = None
        self.safety_status = None
        self.declare_parameter("window_logic_enabled", True)

        self.decision_pub = self.create_publisher(LandingDecisionStatus, "/landing_decision/status", 10)

        self.create_subscription(LandingWindowStatus, "/landing_window/status", self.window_status_cb, 10)
        self.create_subscription(MissionStatus, "/mission/phase", self.mission_status_cb, 10)
        self.create_subscription(SafetyStatus, "/safety/status", self.safety_status_cb, 10)

        self.timer = self.create_timer(0.05, self.publish_decision)
        self.get_logger().info("landing_decision advisory node is running.")

    def window_status_cb(self, msg):
        self.window_status = msg

    def mission_status_cb(self, msg):
        self.mission_status = msg

    def safety_status_cb(self, msg):
        self.safety_status = msg

    def publish_decision(self):
        if self.mission_status is None:
            return

        window_logic_enabled = bool(self.get_parameter("window_logic_enabled").value)
        msg = LandingDecisionStatus()
        msg.header.stamp = self.get_clock().now().to_msg()

        if self.safety_status is not None and self.safety_status.abort_requested:
            msg.advisory = LandingDecisionStatus.ABORT
            msg.reason_codes = [self.safety_status.reason or "safety_abort"]
        elif self.mission_status.phase == MissionStatus.ABORT_GO_AROUND:
            msg.advisory = LandingDecisionStatus.GO_AROUND
            msg.reason_codes = ["mission_abort_go_around"]
        elif not window_logic_enabled:
            if self.mission_status.phase in (
                MissionStatus.SEARCH,
                MissionStatus.APPROACH,
                MissionStatus.ALIGN,
            ):
                msg.advisory = LandingDecisionStatus.HOLD
                msg.reason_codes = ["window_logic_disabled_phase_hold"]
            else:
                msg.advisory = LandingDecisionStatus.CONTINUE
                msg.reason_codes = ["window_logic_disabled"]
        elif self.window_status is None:
            msg.advisory = LandingDecisionStatus.HOLD
            msg.reason_codes = ["window_status_unavailable"]
        elif self.mission_status.phase in (
            MissionStatus.SEARCH,
            MissionStatus.APPROACH,
            MissionStatus.ALIGN,
        ):
            msg.advisory = LandingDecisionStatus.HOLD
            msg.reason_codes = ["phase_not_ready_for_window"]
        elif self.mission_status.phase in (MissionStatus.SYNCHRONIZE, MissionStatus.WINDOW_WAIT):
            if self.window_status.window_open:
                msg.advisory = LandingDecisionStatus.CONTINUE
                msg.reason_codes = [self.window_status.window_reason]
            else:
                msg.advisory = LandingDecisionStatus.HOLD
                msg.reason_codes = [self.window_status.window_reason]
        elif self.mission_status.phase == MissionStatus.TERMINAL_DESCENT:
            msg.advisory = LandingDecisionStatus.CONTINUE
            msg.reason_codes = ["terminal_descent_active"]
        else:
            msg.advisory = LandingDecisionStatus.CONTINUE
            msg.reason_codes = ["nominal_progress"]

        self.decision_pub.publish(msg)


def main():
    rclpy.init()
    node = DecisionAdvisoryNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
