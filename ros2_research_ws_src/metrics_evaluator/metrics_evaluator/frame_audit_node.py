import json
import math
import os

from rclpy.node import Node
import rclpy
from std_msgs.msg import Bool, String
from mission_stack_msgs.msg import (
    ExperimentRunStatus,
    LandingZoneState,
    PlatformState,
    RelativeState,
    UavState,
)


def quat_conjugate(q):
    return [-q[0], -q[1], -q[2], q[3]]


def rotate_vector(q, vector):
    x, y, z, w = q
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z

    return [
        (1.0 - 2.0 * (yy + zz)) * vector[0] + 2.0 * (xy - wz) * vector[1] + 2.0 * (xz + wy) * vector[2],
        2.0 * (xy + wz) * vector[0] + (1.0 - 2.0 * (xx + zz)) * vector[1] + 2.0 * (yz - wx) * vector[2],
        2.0 * (xz - wy) * vector[0] + 2.0 * (yz + wx) * vector[1] + (1.0 - 2.0 * (xx + yy)) * vector[2],
    ]


class FrameAuditNode(Node):
    def __init__(self):
        super().__init__("frame_audit")

        self.platform_state = None
        self.zone_state = None
        self.uav_state = None
        self.relative_state = None
        self.output_dir = ""
        self.report_written = False

        self.declare_parameter("expected_target_offset_xyz", [0.5, 0.0, 0.0])
        self.declare_parameter("target_offset_tolerance", 0.05)
        self.declare_parameter("relative_position_tolerance", 0.05)
        self.declare_parameter("relative_velocity_tolerance", 0.1)

        self.status_pub = self.create_publisher(Bool, "/metrics/frame_audit/passed", 10)
        self.report_pub = self.create_publisher(String, "/metrics/frame_audit/report", 10)

        self.create_subscription(PlatformState, "/platform/state", self.platform_state_cb, 10)
        self.create_subscription(
            LandingZoneState, "/platform/landing_zone_state", self.zone_state_cb, 10
        )
        self.create_subscription(UavState, "/uav/state_truth", self.uav_state_cb, 10)
        self.create_subscription(RelativeState, "/relative_state/truth", self.relative_state_cb, 10)
        self.create_subscription(ExperimentRunStatus, "/experiment/run_status", self.run_status_cb, 10)

        self.timer = self.create_timer(1.0, self.evaluate)
        self.get_logger().info("metrics_evaluator frame audit helper is running.")

    def platform_state_cb(self, msg):
        self.platform_state = msg

    def zone_state_cb(self, msg):
        self.zone_state = msg

    def uav_state_cb(self, msg):
        self.uav_state = msg

    def relative_state_cb(self, msg):
        self.relative_state = msg

    def run_status_cb(self, msg):
        self.output_dir = msg.output_dir

    def evaluate(self):
        if not all([self.platform_state, self.zone_state, self.uav_state, self.relative_state]):
            return

        expected_offset = list(self.get_parameter("expected_target_offset_xyz").value)
        target_offset_tolerance = float(self.get_parameter("target_offset_tolerance").value)
        relative_position_tolerance = float(self.get_parameter("relative_position_tolerance").value)
        relative_velocity_tolerance = float(self.get_parameter("relative_velocity_tolerance").value)

        deck_q = [
            self.platform_state.pose.orientation.x,
            self.platform_state.pose.orientation.y,
            self.platform_state.pose.orientation.z,
            self.platform_state.pose.orientation.w,
        ]
        target_q = [
            self.zone_state.center_pose.orientation.x,
            self.zone_state.center_pose.orientation.y,
            self.zone_state.center_pose.orientation.z,
            self.zone_state.center_pose.orientation.w,
        ]
        target_q_inv = quat_conjugate(target_q)

        target_delta_world = [
            self.zone_state.center_pose.position.x - self.platform_state.pose.position.x,
            self.zone_state.center_pose.position.y - self.platform_state.pose.position.y,
            self.zone_state.center_pose.position.z - self.platform_state.pose.position.z,
        ]
        target_delta_deck = rotate_vector(quat_conjugate(deck_q), target_delta_world)

        world_relative_position = [
            self.uav_state.pose.position.x - self.zone_state.center_pose.position.x,
            self.uav_state.pose.position.y - self.zone_state.center_pose.position.y,
            self.uav_state.pose.position.z - self.zone_state.center_pose.position.z,
        ]
        world_relative_velocity = [
            self.uav_state.twist.linear.x - self.zone_state.twist.linear.x,
            self.uav_state.twist.linear.y - self.zone_state.twist.linear.y,
            self.uav_state.twist.linear.z - self.zone_state.twist.linear.z,
        ]

        relative_position_target = rotate_vector(target_q_inv, world_relative_position)
        relative_velocity_target = rotate_vector(target_q_inv, world_relative_velocity)

        target_offset_error = math.sqrt(
            sum((target_delta_deck[i] - expected_offset[i]) ** 2 for i in range(3))
        )
        relative_position_error = math.sqrt(
            (relative_position_target[0] - self.relative_state.position.x) ** 2
            + (relative_position_target[1] - self.relative_state.position.y) ** 2
            + (relative_position_target[2] - self.relative_state.position.z) ** 2
        )
        relative_velocity_error = math.sqrt(
            (relative_velocity_target[0] - self.relative_state.linear_velocity.x) ** 2
            + (relative_velocity_target[1] - self.relative_state.linear_velocity.y) ** 2
            + (relative_velocity_target[2] - self.relative_state.linear_velocity.z) ** 2
        )

        passed = (
            target_offset_error <= target_offset_tolerance
            and relative_position_error <= relative_position_tolerance
            and relative_velocity_error <= relative_velocity_tolerance
        )

        report = {
            "passed": passed,
            "target_offset_error": target_offset_error,
            "relative_position_error": relative_position_error,
            "relative_velocity_error": relative_velocity_error,
            "expected_target_offset_xyz": expected_offset,
            "measured_target_offset_in_deck_frame_xyz": target_delta_deck,
        }

        self.status_pub.publish(Bool(data=passed))
        self.report_pub.publish(String(data=json.dumps(report, sort_keys=True)))

        if self.output_dir and not self.report_written:
            os.makedirs(self.output_dir, exist_ok=True)
            with open(os.path.join(self.output_dir, "frame_audit_report.json"), "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, sort_keys=True)
            self.report_written = True


def main():
    rclpy.init()
    node = FrameAuditNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
