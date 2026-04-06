from datetime import datetime
import json
import os

import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import (
    ExperimentEvent,
    ExperimentRunStatus,
    LandingDecisionStatus,
    LandingWindowStatus,
    MissionStatus,
    ScenarioProfile,
    SafetyStatus,
    TouchdownEvent,
)


class ScenarioRunner(Node):
    def __init__(self):
        super().__init__("experiment_manager")

        self.declare_parameter("scenario_id", "calm_truth")
        self.declare_parameter("run_id", "")
        self.declare_parameter("seed", 42)
        self.declare_parameter("mode", "baseline_minimal")
        self.declare_parameter("output_root", os.path.expanduser("~/uav-landing-experiment-runs"))
        self.declare_parameter("platform_type", "deck")
        self.declare_parameter("motion_profile", "truth")
        self.declare_parameter("default_planner_backend", "baseline")
        self.declare_parameter("default_reference_source", "guidance")
        self.declare_parameter("planner_required", False)
        self.declare_parameter("allow_planner_active_path", True)
        self.declare_parameter("planner_shadow_mode", False)
        self.declare_parameter("window_logic_enabled", False)
        self.declare_parameter("decision_logic_enabled", False)
        self.declare_parameter("enable_decision", False)
        self.declare_parameter("enable_planner", True)
        self.declare_parameter("enable_safety", True)
        self.declare_parameter("enable_touchdown", True)
        self.declare_parameter("relative_state_source", "truth")
        self.declare_parameter("platform_state_source", "bridge")
        self.declare_parameter("landing_zone_state_source", "bridge")
        self.declare_parameter("uav_state_source", "truth")
        self.declare_parameter("phase_profile", "baseline")
        self.declare_parameter("metrics_profile", "baseline")
        self.declare_parameter(
            "enabled_modules",
            [
                "platform_interface",
                "relative_estimation",
                "mission_manager",
                "landing_guidance",
                "trajectory_planner",
                "controller_interface",
                "touchdown_manager",
                "experiment_manager",
                "metrics_evaluator",
            ],
        )

        self.scenario_id = str(self.get_parameter("scenario_id").value)
        self.run_id = str(self.get_parameter("run_id").value) or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.seed = int(self.get_parameter("seed").value)
        self.mode = str(self.get_parameter("mode").value)
        self.output_root = os.path.expanduser(str(self.get_parameter("output_root").value))
        self.output_dir = ""
        self.current_phase = MissionStatus.SEARCH
        self.last_phase = None
        self.last_window_signature = None
        self.last_decision_signature = None
        self.last_safety_signature = None

        self.run_status_pub = self.create_publisher(ExperimentRunStatus, "/experiment/run_status", 10)
        self.scenario_profile_pub = self.create_publisher(
            ScenarioProfile, "/experiment/scenario_profile", 10
        )
        self.event_pub = self.create_publisher(ExperimentEvent, "/experiment/events", 10)

        self.prepare_output_dir()

        self.create_subscription(MissionStatus, "/mission/phase", self.phase_cb, 10)
        self.create_subscription(LandingWindowStatus, "/landing_window/status", self.window_cb, 10)
        self.create_subscription(LandingDecisionStatus, "/landing_decision/status", self.decision_cb, 10)
        self.create_subscription(SafetyStatus, "/safety/status", self.safety_cb, 10)
        self.create_subscription(TouchdownEvent, "/touchdown/event", self.touchdown_event_cb, 10)

        self.timer = self.create_timer(1.0, self.publish_metadata)
        self.emit_event("experiment_manager", "run", "run_started", "experiment run started")
        self.get_logger().info(
            f"experiment_manager is running. scenario_id={self.scenario_id}, run_id={self.run_id}, output_dir={self.output_dir}"
        )

    def prepare_output_dir(self):
        if not self.output_root:
            self.output_dir = ""
            return

        self.output_dir = os.path.join(self.output_root, self.scenario_id, self.run_id)
        os.makedirs(self.output_dir, exist_ok=True)

        metadata = {
            "scenario_id": self.scenario_id,
            "run_id": self.run_id,
            "seed": self.seed,
            "mode": self.mode,
            "created_at": datetime.now().isoformat(),
            "output_dir": self.output_dir,
        }

        with open(os.path.join(self.output_dir, "run_metadata.json"), "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, sort_keys=True)

        scenario_yaml = "\n".join(
            [
                f"scenario_id: {self.scenario_id}",
                f"run_id: {self.run_id}",
                f"seed: {self.seed}",
                f"mode: {self.mode}",
                f"output_dir: {self.output_dir}",
            ]
        )
        with open(os.path.join(self.output_dir, "scenario.yaml"), "w", encoding="utf-8") as handle:
            handle.write(scenario_yaml + "\n")

    def append_event_record(self, record):
        if not self.output_dir:
            return

        with open(os.path.join(self.output_dir, "events.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def emit_event(self, source_pkg, event_type, code, text):
        msg = ExperimentEvent()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.source_pkg = source_pkg
        msg.event_type = event_type
        msg.code = code
        msg.phase = self.current_phase
        msg.text = text
        self.event_pub.publish(msg)
        self.append_event_record(
            {
                "stamp": {"sec": msg.header.stamp.sec, "nanosec": msg.header.stamp.nanosec},
                "source_pkg": source_pkg,
                "event_type": event_type,
                "code": code,
                "phase": int(self.current_phase),
                "text": text,
            }
        )

    def phase_cb(self, msg):
        self.current_phase = msg.phase
        if self.last_phase != msg.phase:
            self.last_phase = msg.phase
            self.emit_event("mission_manager", "mission_phase", str(msg.phase), msg.transition_reason)

    def window_cb(self, msg):
        signature = (bool(msg.window_open), str(msg.window_reason))
        if signature != self.last_window_signature:
            self.last_window_signature = signature
            code = "window_open" if msg.window_open else "window_closed"
            self.emit_event("landing_decision", "landing_window", code, msg.window_reason)

    def decision_cb(self, msg):
        signature = (int(msg.advisory), tuple(msg.reason_codes))
        if signature != self.last_decision_signature:
            self.last_decision_signature = signature
            self.emit_event(
                "landing_decision",
                "decision_advisory",
                str(msg.advisory),
                ",".join(msg.reason_codes),
            )

    def safety_cb(self, msg):
        signature = (bool(msg.abort_requested), str(msg.reason))
        if signature != self.last_safety_signature:
            self.last_safety_signature = signature
            self.emit_event("safety_manager", "safety_status", msg.reason, msg.reason)

    def touchdown_event_cb(self, msg):
        self.emit_event("touchdown_manager", "touchdown_event", msg.event_type, msg.reason)

    def publish_metadata(self):
        scenario_msg = ScenarioProfile()
        scenario_msg.header.stamp = self.get_clock().now().to_msg()
        scenario_msg.scenario_id = self.scenario_id
        scenario_msg.platform_type = str(self.get_parameter("platform_type").value)
        scenario_msg.motion_profile = str(self.get_parameter("motion_profile").value)
        scenario_msg.default_planner_backend = str(
            self.get_parameter("default_planner_backend").value
        )
        scenario_msg.default_reference_source = str(
            self.get_parameter("default_reference_source").value
        )
        scenario_msg.planner_required = bool(self.get_parameter("planner_required").value)
        scenario_msg.allow_planner_active_path = bool(
            self.get_parameter("allow_planner_active_path").value
        )
        scenario_msg.planner_shadow_mode = bool(
            self.get_parameter("planner_shadow_mode").value
        )
        scenario_msg.window_logic_enabled = bool(
            self.get_parameter("window_logic_enabled").value
        )
        scenario_msg.decision_logic_enabled = bool(
            self.get_parameter("decision_logic_enabled").value
        )
        scenario_msg.enable_decision = bool(self.get_parameter("enable_decision").value)
        scenario_msg.enable_planner = bool(self.get_parameter("enable_planner").value)
        scenario_msg.enable_safety = bool(self.get_parameter("enable_safety").value)
        scenario_msg.enable_touchdown = bool(self.get_parameter("enable_touchdown").value)
        scenario_msg.relative_state_source = str(
            self.get_parameter("relative_state_source").value
        )
        scenario_msg.platform_state_source = str(
            self.get_parameter("platform_state_source").value
        )
        scenario_msg.landing_zone_state_source = str(
            self.get_parameter("landing_zone_state_source").value
        )
        scenario_msg.uav_state_source = str(self.get_parameter("uav_state_source").value)
        scenario_msg.phase_profile = str(self.get_parameter("phase_profile").value)
        scenario_msg.metrics_profile = str(self.get_parameter("metrics_profile").value)
        scenario_msg.enabled_modules = [
            str(item) for item in self.get_parameter("enabled_modules").value
        ]
        self.scenario_profile_pub.publish(scenario_msg)

        msg = ExperimentRunStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.scenario_id = self.scenario_id
        msg.run_id = self.run_id
        msg.seed = self.seed
        msg.output_dir = self.output_dir
        msg.mode = self.mode
        msg.state = "running"
        self.run_status_pub.publish(msg)


def main():
    rclpy.init()
    node = ScenarioRunner()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
