import json
import math
import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from mission_stack_msgs.msg import (
    ExperimentRunStatus,
    LandingZoneState,
    PlatformState,
    RelativeState,
    UavState,
)


def stamp_to_sec(stamp):
    return float(stamp.sec) + float(stamp.nanosec) * 1e-9


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


def yaw_from_quaternion(q):
    siny_cosp = 2.0 * (q[3] * q[2] + q[0] * q[1])
    cosy_cosp = 1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
    return math.atan2(siny_cosp, cosy_cosp)


def yaw_error_rad(q1, q2):
    yaw_1 = yaw_from_quaternion(q1)
    yaw_2 = yaw_from_quaternion(q2)
    delta = yaw_1 - yaw_2
    return abs(math.atan2(math.sin(delta), math.cos(delta)))


class GeometryConsistencyNode(Node):
    def __init__(self):
        super().__init__("geometry_consistency")

        self.declare_parameter("stable_topic_window_sec", 2.0)
        self.declare_parameter("sample_window_sec", 10.0)
        self.declare_parameter("reference_frame", "world")
        self.declare_parameter("expected_landing_zone_offset_xyz", [0.5, 0.0, 0.0])
        self.declare_parameter("platform_offset_tolerance", 0.10)
        self.declare_parameter("relative_position_tolerance", 0.20)
        self.declare_parameter("relative_velocity_tolerance", 0.20)
        self.declare_parameter("zero_offset_position_tolerance", 0.01)
        self.declare_parameter("zero_offset_yaw_tolerance", 0.01)
        self.declare_parameter("required_zero_offset_alignment", False)

        self.platform_state = None
        self.zone_state = None
        self.uav_state = None
        self.relative_state = None
        self.output_dir = ""
        self.report_written = False
        self.stable_candidate_start = None
        self.sample_window_start = None
        self.sample_window_end = None
        self.sample_drop_detected = False
        self.topic_names = {
            "platform_state": "/platform/state",
            "landing_zone_state": "/platform/landing_zone_state",
            "uav_state_truth": "/uav/state_truth",
            "relative_state_active": "/relative_state/active",
        }
        self.topic_meta = {
            name: {
                "last_receive_sec": None,
                "last_header_sec": None,
                "stamp_regression": False,
                "sample_count": 0,
            }
            for name in self.topic_names
        }

        self.status_pub = self.create_publisher(Bool, "/metrics/geometry_consistency/passed", 10)
        self.report_pub = self.create_publisher(String, "/metrics/geometry_consistency/report", 10)

        self.create_subscription(PlatformState, "/platform/state", self.platform_state_cb, 10)
        self.create_subscription(
            LandingZoneState, "/platform/landing_zone_state", self.zone_state_cb, 10
        )
        self.create_subscription(UavState, "/uav/state_truth", self.uav_state_cb, 10)
        self.create_subscription(RelativeState, "/relative_state/active", self.relative_state_cb, 10)
        self.create_subscription(ExperimentRunStatus, "/experiment/run_status", self.run_status_cb, 10)

        self.timer = self.create_timer(0.2, self.evaluate)
        self.get_logger().info("metrics_evaluator geometry consistency helper is running.")

    def now_sec(self):
        return stamp_to_sec(self.get_clock().now().to_msg())

    def note_topic(self, topic_name, msg):
        meta = self.topic_meta[topic_name]
        header_sec = stamp_to_sec(msg.header.stamp)
        if meta["last_header_sec"] is not None and header_sec + 1e-9 < meta["last_header_sec"]:
            meta["stamp_regression"] = True
        meta["last_header_sec"] = header_sec
        meta["last_receive_sec"] = self.now_sec()
        if self.sample_window_start is not None and not self.report_written:
            meta["sample_count"] += 1

    def platform_state_cb(self, msg):
        self.platform_state = msg
        self.note_topic("platform_state", msg)

    def zone_state_cb(self, msg):
        self.zone_state = msg
        self.note_topic("landing_zone_state", msg)

    def uav_state_cb(self, msg):
        self.uav_state = msg
        self.note_topic("uav_state_truth", msg)

    def relative_state_cb(self, msg):
        self.relative_state = msg
        self.note_topic("relative_state_active", msg)

    def run_status_cb(self, msg):
        self.output_dir = msg.output_dir

    def topics_are_live(self, now_sec):
        for meta in self.topic_meta.values():
            if meta["last_receive_sec"] is None:
                return False
            if now_sec - meta["last_receive_sec"] > float(
                self.get_parameter("stable_topic_window_sec").value
            ):
                return False
            if meta["stamp_regression"]:
                return False
        return True

    def evaluate(self):
        if self.report_written or not all(
            [self.platform_state, self.zone_state, self.uav_state, self.relative_state]
        ):
            return

        now_sec = self.now_sec()
        stable_window_sec = float(self.get_parameter("stable_topic_window_sec").value)
        sample_window_sec = float(self.get_parameter("sample_window_sec").value)

        if self.sample_window_start is None:
            if self.topics_are_live(now_sec):
                if self.stable_candidate_start is None:
                    self.stable_candidate_start = now_sec
                if now_sec - self.stable_candidate_start >= stable_window_sec:
                    self.sample_window_start = now_sec
                    self.sample_window_end = now_sec + sample_window_sec
                    for meta in self.topic_meta.values():
                        meta["sample_count"] = 0
            else:
                self.stable_candidate_start = None
            return

        if not self.topics_are_live(now_sec):
            self.sample_drop_detected = True

        if now_sec < self.sample_window_end:
            return

        report = self.build_report()
        self.status_pub.publish(Bool(data=report["pass_fail"]))
        self.report_pub.publish(String(data=json.dumps(report, sort_keys=True)))

        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            with open(
                os.path.join(self.output_dir, "geometry_consistency_report.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(report, handle, indent=2, sort_keys=True)

        self.report_written = True

    def build_report(self):
        expected_offset = list(self.get_parameter("expected_landing_zone_offset_xyz").value)
        platform_offset_tolerance = float(self.get_parameter("platform_offset_tolerance").value)
        relative_position_tolerance = float(
            self.get_parameter("relative_position_tolerance").value
        )
        relative_velocity_tolerance = float(
            self.get_parameter("relative_velocity_tolerance").value
        )
        zero_offset_position_tolerance = float(
            self.get_parameter("zero_offset_position_tolerance").value
        )
        zero_offset_yaw_tolerance = float(
            self.get_parameter("zero_offset_yaw_tolerance").value
        )
        required_zero_offset_alignment = bool(
            self.get_parameter("required_zero_offset_alignment").value
        )

        platform_q = [
            self.platform_state.pose.orientation.x,
            self.platform_state.pose.orientation.y,
            self.platform_state.pose.orientation.z,
            self.platform_state.pose.orientation.w,
        ]
        zone_q = [
            self.zone_state.center_pose.orientation.x,
            self.zone_state.center_pose.orientation.y,
            self.zone_state.center_pose.orientation.z,
            self.zone_state.center_pose.orientation.w,
        ]
        zone_q_inv = quat_conjugate(zone_q)

        landing_zone_delta_world = [
            self.zone_state.center_pose.position.x - self.platform_state.pose.position.x,
            self.zone_state.center_pose.position.y - self.platform_state.pose.position.y,
            self.zone_state.center_pose.position.z - self.platform_state.pose.position.z,
        ]
        landing_zone_delta_platform = rotate_vector(quat_conjugate(platform_q), landing_zone_delta_world)

        relative_position_world = [
            self.uav_state.pose.position.x - self.zone_state.center_pose.position.x,
            self.uav_state.pose.position.y - self.zone_state.center_pose.position.y,
            self.uav_state.pose.position.z - self.zone_state.center_pose.position.z,
        ]
        relative_velocity_world = [
            self.uav_state.twist.linear.x - self.zone_state.twist.linear.x,
            self.uav_state.twist.linear.y - self.zone_state.twist.linear.y,
            self.uav_state.twist.linear.z - self.zone_state.twist.linear.z,
        ]
        relative_position_target = rotate_vector(zone_q_inv, relative_position_world)
        relative_velocity_target = rotate_vector(zone_q_inv, relative_velocity_world)

        platform_offset_error = math.sqrt(
            sum(
                (landing_zone_delta_platform[idx] - expected_offset[idx]) ** 2
                for idx in range(3)
            )
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
        zero_offset_position_error = math.sqrt(
            landing_zone_delta_world[0] ** 2
            + landing_zone_delta_world[1] ** 2
            + landing_zone_delta_world[2] ** 2
        )
        zero_offset_yaw_error = yaw_error_rad(platform_q, zone_q)

        sample_counts = {
            self.topic_names[name]: int(meta["sample_count"])
            for name, meta in self.topic_meta.items()
        }
        stamp_regressions = {
            self.topic_names[name]: bool(meta["stamp_regression"])
            for name, meta in self.topic_meta.items()
        }

        zero_alignment_ok = True
        if required_zero_offset_alignment:
            zero_alignment_ok = (
                zero_offset_position_error <= zero_offset_position_tolerance
                and zero_offset_yaw_error <= zero_offset_yaw_tolerance
            )

        pass_fail = (
            not self.sample_drop_detected
            and not any(stamp_regressions.values())
            and all(count > 0 for count in sample_counts.values())
            and platform_offset_error <= platform_offset_tolerance
            and relative_position_error <= relative_position_tolerance
            and relative_velocity_error <= relative_velocity_tolerance
            and zero_alignment_ok
        )

        return {
            "topics_used": list(self.topic_names.values()),
            "sample_window_start": self.sample_window_start,
            "sample_window_end": self.sample_window_end,
            "sample_count": sample_counts,
            "reference_frame": str(self.get_parameter("reference_frame").value),
            "thresholds": {
                "stable_topic_window_sec": float(
                    self.get_parameter("stable_topic_window_sec").value
                ),
                "sample_window_sec": float(self.get_parameter("sample_window_sec").value),
                "platform_offset_tolerance": platform_offset_tolerance,
                "relative_position_tolerance": relative_position_tolerance,
                "relative_velocity_tolerance": relative_velocity_tolerance,
                "zero_offset_position_tolerance": zero_offset_position_tolerance,
                "zero_offset_yaw_tolerance": zero_offset_yaw_tolerance,
            },
            "measured_errors": {
                "platform_offset_error": platform_offset_error,
                "relative_position_error": relative_position_error,
                "relative_velocity_error": relative_velocity_error,
                "zero_offset_position_error": zero_offset_position_error,
                "zero_offset_yaw_error": zero_offset_yaw_error,
            },
            "expected_landing_zone_offset_xyz": expected_offset,
            "measured_landing_zone_offset_in_platform_frame_xyz": landing_zone_delta_platform,
            "stamp_regressions": stamp_regressions,
            "sample_drop_detected": self.sample_drop_detected,
            "required_zero_offset_alignment": required_zero_offset_alignment,
            "pass_fail": pass_fail,
        }


def main():
    rclpy.init()
    node = GeometryConsistencyNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
