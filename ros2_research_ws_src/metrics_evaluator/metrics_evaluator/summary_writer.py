import csv
import json
import math
import os
from time import monotonic

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from mission_stack_msgs.msg import (
    ExperimentRunStatus,
    LandingDecisionStatus,
    LandingWindowStatus,
    LandingZoneState,
    MetricsSummary,
    MissionStatus,
    PlannerStatus,
    PlatformState,
    RelativeState,
    SafetyStatus,
    ScenarioProfile,
    TouchdownState,
)


class SummaryWriter(Node):
    def __init__(self):
        super().__init__("metrics_evaluator")

        self.declare_parameter("chain_validation_mode", False)
        self.declare_parameter("minimum_observation_sec", 35.0)
        self.declare_parameter("required_topic_runtime_sec", 30.0)
        self.declare_parameter("minimum_phase_dwell_sec", 1.0)
        self.declare_parameter("topic_dropout_tolerance_sec", 2.5)
        self.declare_parameter("require_platform_motion", False)
        self.declare_parameter("minimum_platform_displacement_m", 1.0)
        self.declare_parameter("motion_warmup_sec", 5.0)
        self.declare_parameter("motion_eval_duration_sec", 10.0)

        self.relative_state = None
        self.platform_state = None
        self.zone_state = None
        self.mission_status = None
        self.safety_status = None
        self.touchdown_state = None
        self.run_status = None
        self.scenario_profile = None
        self.frame_audit_passed = None
        self.geometry_consistency_passed = None

        self.last_decision_advisory = None
        self.max_xy_error = 0.0
        self.summary_written = False
        self.start_monotonic = monotonic()
        self.sample_count = 0
        self.go_around_count = 0
        self.safety_violation_count = 0
        self.window_total_samples = 0
        self.window_open_samples = 0

        self.phase_history = []
        self.phase_enter_monotonic = None
        self.current_phase = None
        self.search_seen = False
        self.stable_downstream_phase_seen = False

        self.topic_stats = {
            "platform_state": self.make_topic_stat(),
            "landing_zone_state": self.make_topic_stat(),
            "relative_state_active": self.make_topic_stat(),
            "mission_phase": self.make_topic_stat(),
            "planner_status": self.make_topic_stat(),
            "experiment_run_status": self.make_topic_stat(),
            "scenario_profile": self.make_topic_stat(),
        }

        self.platform_motion_start_pose = None
        self.platform_motion_end_pose = None
        self.platform_motion_start_time = None

        self.summary_pub = self.create_publisher(MetricsSummary, "/metrics/summary", 10)

        self.create_subscription(RelativeState, "/relative_state/active", self.relative_state_cb, 10)
        self.create_subscription(PlatformState, "/platform/state", self.platform_state_cb, 10)
        self.create_subscription(
            LandingZoneState, "/platform/landing_zone_state", self.zone_state_cb, 10
        )
        self.create_subscription(MissionStatus, "/mission/phase", self.mission_status_cb, 10)
        self.create_subscription(PlannerStatus, "/planner/status", self.planner_status_cb, 10)
        self.create_subscription(SafetyStatus, "/safety/status", self.safety_status_cb, 10)
        self.create_subscription(TouchdownState, "/touchdown/state", self.touchdown_state_cb, 10)
        self.create_subscription(ExperimentRunStatus, "/experiment/run_status", self.run_status_cb, 10)
        self.create_subscription(
            ScenarioProfile, "/experiment/scenario_profile", self.scenario_profile_cb, 10
        )
        self.create_subscription(
            LandingDecisionStatus, "/landing_decision/status", self.decision_status_cb, 10
        )
        self.create_subscription(LandingWindowStatus, "/landing_window/status", self.window_status_cb, 10)
        self.create_subscription(Bool, "/metrics/frame_audit/passed", self.frame_audit_cb, 10)
        self.create_subscription(
            Bool, "/metrics/geometry_consistency/passed", self.geometry_consistency_cb, 10
        )

        self.timer = self.create_timer(1.0, self.maybe_write_summary)
        self.get_logger().info("metrics_evaluator summary writer is running.")

    def make_topic_stat(self):
        return {
            "first_arrival_monotonic": None,
            "last_arrival_monotonic": None,
            "last_header_sec": None,
            "gap_violation": False,
            "stamp_regression": False,
            "count": 0,
        }

    def note_topic(self, name, msg):
        stat = self.topic_stats[name]
        now = monotonic()
        header_sec = float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9
        if stat["first_arrival_monotonic"] is None:
            stat["first_arrival_monotonic"] = now
        if (
            stat["last_arrival_monotonic"] is not None
            and now - stat["last_arrival_monotonic"]
            > float(self.get_parameter("topic_dropout_tolerance_sec").value)
        ):
            stat["gap_violation"] = True
        if stat["last_header_sec"] is not None and header_sec + 1e-9 < stat["last_header_sec"]:
            stat["stamp_regression"] = True

        stat["last_arrival_monotonic"] = now
        stat["last_header_sec"] = header_sec
        stat["count"] += 1

    def relative_state_cb(self, msg):
        self.relative_state = msg
        self.note_topic("relative_state_active", msg)
        xy_error = math.hypot(msg.position.x, msg.position.y)
        self.max_xy_error = max(self.max_xy_error, xy_error)
        self.sample_count += 1

    def platform_state_cb(self, msg):
        self.platform_state = msg
        self.note_topic("platform_state", msg)

        now = monotonic() - self.start_monotonic
        if not bool(self.get_parameter("require_platform_motion").value):
            return

        warmup_sec = float(self.get_parameter("motion_warmup_sec").value)
        eval_duration_sec = float(self.get_parameter("motion_eval_duration_sec").value)
        if now < warmup_sec:
            return
        if self.platform_motion_start_pose is None:
            self.platform_motion_start_pose = (
                msg.pose.position.x,
                msg.pose.position.y,
            )
            self.platform_motion_start_time = now
        if now <= warmup_sec + eval_duration_sec:
            self.platform_motion_end_pose = (
                msg.pose.position.x,
                msg.pose.position.y,
            )

    def zone_state_cb(self, msg):
        self.zone_state = msg
        self.note_topic("landing_zone_state", msg)

    def mission_status_cb(self, msg):
        self.mission_status = msg
        self.note_topic("mission_phase", msg)

        now = monotonic()
        if msg.phase == MissionStatus.SEARCH:
            self.search_seen = True

        if self.current_phase != msg.phase:
            self.current_phase = msg.phase
            self.phase_enter_monotonic = now
            self.phase_history.append(int(msg.phase))

    def planner_status_cb(self, msg):
        self.note_topic("planner_status", msg)

    def safety_status_cb(self, msg):
        if self.safety_status is None or (
            not self.safety_status.abort_requested and msg.abort_requested
        ):
            self.safety_violation_count += int(msg.abort_requested)
        self.safety_status = msg

    def touchdown_state_cb(self, msg):
        self.touchdown_state = msg

    def run_status_cb(self, msg):
        self.run_status = msg
        self.note_topic("experiment_run_status", msg)

    def scenario_profile_cb(self, msg):
        self.scenario_profile = msg
        self.note_topic("scenario_profile", msg)

    def decision_status_cb(self, msg):
        if (
            msg.advisory == LandingDecisionStatus.GO_AROUND
            and self.last_decision_advisory != LandingDecisionStatus.GO_AROUND
        ):
            self.go_around_count += 1
        self.last_decision_advisory = msg.advisory

    def window_status_cb(self, msg):
        self.window_total_samples += 1
        self.window_open_samples += int(msg.window_open)

    def frame_audit_cb(self, msg):
        self.frame_audit_passed = bool(msg.data)

    def geometry_consistency_cb(self, msg):
        self.geometry_consistency_passed = bool(msg.data)

    def update_phase_transition_state(self):
        if self.phase_enter_monotonic is None:
            return

        dwell_sec = monotonic() - self.phase_enter_monotonic
        if (
            self.search_seen
            and self.current_phase in (MissionStatus.APPROACH, MissionStatus.ALIGN)
            and dwell_sec >= float(self.get_parameter("minimum_phase_dwell_sec").value)
        ):
            self.stable_downstream_phase_seen = True

    def topic_runtime_sec(self, name):
        stat = self.topic_stats[name]
        if stat["first_arrival_monotonic"] is None or stat["last_arrival_monotonic"] is None:
            return 0.0
        return stat["last_arrival_monotonic"] - stat["first_arrival_monotonic"]

    def platform_displacement_m(self):
        if self.platform_motion_start_pose is None or self.platform_motion_end_pose is None:
            return 0.0
        dx = self.platform_motion_end_pose[0] - self.platform_motion_start_pose[0]
        dy = self.platform_motion_end_pose[1] - self.platform_motion_start_pose[1]
        return math.hypot(dx, dy)

    def evaluate_chain_validation(self):
        required_topics = [
            "platform_state",
            "landing_zone_state",
            "relative_state_active",
            "mission_phase",
            "planner_status",
            "experiment_run_status",
            "scenario_profile",
        ]
        required_runtime = float(self.get_parameter("required_topic_runtime_sec").value)
        topic_runtimes = {name: self.topic_runtime_sec(name) for name in required_topics}
        topic_status = {}
        failures = []

        for name in required_topics:
            stat = self.topic_stats[name]
            topic_ok = (
                stat["count"] > 0
                and topic_runtimes[name] >= required_runtime
                and not stat["gap_violation"]
                and not stat["stamp_regression"]
            )
            topic_status[name] = topic_ok
            if not topic_ok:
                failures.append(f"topic_not_stable:{name}")

        mission_success_seen = bool(
            self.touchdown_state is not None
            and self.touchdown_state.landing_completed
            and not self.touchdown_state.landing_failed
        )
        phase_ok = (
            self.search_seen and self.stable_downstream_phase_seen
        ) or mission_success_seen
        if not phase_ok:
            failures.append("phase_flow_not_stable")

        frame_ok = bool(self.frame_audit_passed)
        if not frame_ok:
            failures.append("frame_audit_failed")

        geometry_ok = bool(self.geometry_consistency_passed)
        if not geometry_ok:
            failures.append("geometry_consistency_failed")

        platform_displacement_m = self.platform_displacement_m()
        motion_ok = True
        if bool(self.get_parameter("require_platform_motion").value):
            motion_ok = (
                platform_displacement_m
                >= float(self.get_parameter("minimum_platform_displacement_m").value)
            )
            if not motion_ok:
                failures.append("platform_motion_below_threshold")

        return (
            len(failures) == 0,
            {
                "topic_status": topic_status,
                "topic_runtime_sec": topic_runtimes,
                "frame_audit_passed": frame_ok,
                "geometry_consistency_passed": geometry_ok,
                "search_seen": self.search_seen,
                "stable_downstream_phase_seen": self.stable_downstream_phase_seen,
                "mission_success_override_phase_gate": mission_success_seen,
                "observed_phases": list(self.phase_history),
                "platform_displacement_m": platform_displacement_m,
                "failures": failures,
            },
        )

    def should_write_chain_summary(self):
        return (
            bool(self.get_parameter("chain_validation_mode").value)
            and monotonic() - self.start_monotonic
            >= float(self.get_parameter("minimum_observation_sec").value)
            and self.relative_state is not None
            and self.run_status is not None
        )

    def mission_complete(self):
        return (
            self.touchdown_state is not None and self.touchdown_state.landing_completed
        ) or (
            self.mission_status is not None
            and self.mission_status.phase
            in (MissionStatus.POST_LANDING, MissionStatus.ABORT_GO_AROUND)
        ) or (
            self.safety_status is not None and self.safety_status.abort_requested
        )

    def maybe_write_summary(self):
        if self.summary_written or self.relative_state is None or self.run_status is None:
            return

        self.update_phase_transition_state()

        chain_validation_mode = bool(self.get_parameter("chain_validation_mode").value)
        if not chain_validation_mode and not self.mission_complete():
            return
        if chain_validation_mode and not self.should_write_chain_summary():
            return

        window_utilization = (
            float(self.window_open_samples) / float(self.window_total_samples)
            if self.window_total_samples
            else 0.0
        )
        touchdown_speed = math.sqrt(
            self.relative_state.linear_velocity.x ** 2
            + self.relative_state.linear_velocity.y ** 2
            + self.relative_state.linear_velocity.z ** 2
        )
        mission_success = bool(
            self.touchdown_state is not None
            and self.touchdown_state.landing_completed
            and not self.touchdown_state.landing_failed
        )
        mission_outcome = "success" if mission_success else "aborted_or_failed"

        chain_validation_passed = False
        chain_details = {}
        if chain_validation_mode:
            chain_validation_passed, chain_details = self.evaluate_chain_validation()

        msg = MetricsSummary()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.mission_success = mission_success
        msg.outcome_label = mission_outcome
        msg.terminal_xy_error = math.hypot(self.relative_state.position.x, self.relative_state.position.y)
        msg.terminal_z_error = self.relative_state.position.z
        msg.touchdown_speed = touchdown_speed
        msg.go_around_count = self.go_around_count
        msg.safety_violation_count = self.safety_violation_count
        msg.window_utilization = window_utilization
        self.summary_pub.publish(msg)

        summary = {
            "scenario_id": self.run_status.scenario_id,
            "run_id": self.run_status.run_id,
            "phase": self.mission_status.phase if self.mission_status is not None else -1,
            "safety_reason": self.safety_status.reason if self.safety_status is not None else "unknown",
            "abort_requested": bool(self.safety_status.abort_requested) if self.safety_status else False,
            "landing_completed": bool(self.touchdown_state.landing_completed) if self.touchdown_state else False,
            "landing_failed": bool(self.touchdown_state.landing_failed) if self.touchdown_state else False,
            "mission_outcome": mission_outcome,
            "outcome_label": mission_outcome,
            "mission_success": mission_success,
            "chain_validation_passed": chain_validation_passed,
            "frame_audit_passed": bool(self.frame_audit_passed),
            "geometry_consistency_passed": bool(self.geometry_consistency_passed),
            "max_xy_error_m": self.max_xy_error,
            "final_xy_error_m": msg.terminal_xy_error,
            "final_z_error_m": msg.terminal_z_error,
            "touchdown_speed_mps": touchdown_speed,
            "go_around_count": self.go_around_count,
            "safety_violation_count": self.safety_violation_count,
            "window_utilization": window_utilization,
            "samples": self.sample_count,
            "time_to_event_s": monotonic() - self.start_monotonic,
            "stable_phase_transition_observed": self.stable_downstream_phase_seen,
            "observed_phases": list(self.phase_history),
            "platform_displacement_m": self.platform_displacement_m(),
            "chain_validation_details": chain_details,
        }

        if self.run_status.output_dir:
            os.makedirs(self.run_status.output_dir, exist_ok=True)
            with open(os.path.join(self.run_status.output_dir, "summary.json"), "w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2, sort_keys=True)

            csv_path = os.path.join(self.run_status.output_dir, "summary.csv")
            with open(csv_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
                writer.writeheader()
                writer.writerow(summary)

        self.summary_written = True


def main():
    rclpy.init()
    node = SummaryWriter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
