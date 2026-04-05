import copy
import math
from time import perf_counter

from builtin_interfaces.msg import Duration
from geometry_msgs.msg import Twist, Vector3
import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import (
    GuidanceReference,
    LandingDecisionStatus,
    LandingWindowStatus,
    LandingZoneState,
    MissionStatus,
    PlannerStatus,
    PlatformState,
    ReferenceTrajectory,
    ReferenceTrajectoryPoint,
    RelativeState,
    ScenarioProfile,
    TerminalTargetSpec,
)


def yaw_from_quaternion(quaternion):
    siny_cosp = 2.0 * (quaternion.w * quaternion.z + quaternion.x * quaternion.y)
    cosy_cosp = 1.0 - 2.0 * (quaternion.y * quaternion.y + quaternion.z * quaternion.z)
    return math.atan2(siny_cosp, cosy_cosp)


def duration_from_seconds(seconds):
    seconds = max(0.0, float(seconds))
    sec = int(seconds)
    nanosec = int((seconds - sec) * 1e9)
    return Duration(sec=sec, nanosec=nanosec)


def string_param_enabled(value):
    return str(value).strip().lower() not in ("", "scenario_default", "auto")


class PlannerFacadeNode(Node):
    def __init__(self):
        super().__init__("trajectory_planner_node")

        self.relative_state = None
        self.mission_status = None
        self.platform_state = None
        self.zone_state = None
        self.decision_status = None
        self.window_status = None
        self.guidance_reference = None
        self.scenario_profile = None
        self.sequence_id = 0

        self.declare_parameter("planner_backend", "scenario_default")
        self.declare_parameter("publish_rate_hz", 10.0)
        self.declare_parameter("output_horizon_sec", 1.0)
        self.declare_parameter("sampling_dt_sec", 0.1)
        self.declare_parameter("moving_target_lookahead_sec", 0.4)
        self.declare_parameter("approach_height", 5.0)
        self.declare_parameter("align_height", 3.0)
        self.declare_parameter("synchronize_height", 2.0)
        self.declare_parameter("terminal_height", 0.3)
        self.declare_parameter("default_terminal_xy_tolerance", 0.5)
        self.declare_parameter("default_terminal_z_tolerance", 0.25)
        self.declare_parameter("default_heading_tolerance_rad", 0.35)

        self.reference_pub = self.create_publisher(
            ReferenceTrajectory, "/planner/reference_trajectory", 10
        )
        self.status_pub = self.create_publisher(PlannerStatus, "/planner/status", 10)

        self.create_subscription(RelativeState, "/relative_state/active", self.relative_state_cb, 10)
        self.create_subscription(MissionStatus, "/mission/phase", self.mission_status_cb, 10)
        self.create_subscription(
            PlatformState, "/platform/state", self.platform_state_cb, 10
        )
        self.create_subscription(
            LandingZoneState, "/platform/landing_zone_state", self.zone_state_cb, 10
        )
        self.create_subscription(
            LandingDecisionStatus, "/landing_decision/status", self.decision_status_cb, 10
        )
        self.create_subscription(
            LandingWindowStatus, "/landing_window/status", self.window_status_cb, 10
        )
        self.create_subscription(
            GuidanceReference, "/guidance/reference", self.guidance_reference_cb, 10
        )
        self.create_subscription(
            ScenarioProfile, "/experiment/scenario_profile", self.scenario_profile_cb, 10
        )

        publish_rate_hz = max(1.0, float(self.get_parameter("publish_rate_hz").value))
        self.timer = self.create_timer(1.0 / publish_rate_hz, self.publish_plan)
        self.get_logger().info(
            "trajectory_planner facade is running with minimum-input support."
        )

    def relative_state_cb(self, msg):
        self.relative_state = msg

    def mission_status_cb(self, msg):
        self.mission_status = msg

    def platform_state_cb(self, msg):
        self.platform_state = msg

    def zone_state_cb(self, msg):
        self.zone_state = msg

    def decision_status_cb(self, msg):
        self.decision_status = msg

    def window_status_cb(self, msg):
        self.window_status = msg

    def guidance_reference_cb(self, msg):
        self.guidance_reference = msg

    def scenario_profile_cb(self, msg):
        self.scenario_profile = msg

    def resolve_backend_name(self):
        explicit_backend = str(self.get_parameter("planner_backend").value).strip().lower()
        if string_param_enabled(explicit_backend):
            return explicit_backend

        if self.scenario_profile is not None:
            profile_backend = self.scenario_profile.default_planner_backend.strip().lower()
            if profile_backend:
                return profile_backend

        return "baseline"

    def window_logic_enabled(self):
        return bool(
            self.scenario_profile.window_logic_enabled
            if self.scenario_profile is not None
            else False
        )

    def determine_mode(self):
        decision_mode = None
        reason_codes = []
        if self.decision_status is not None:
            advisory = self.decision_status.advisory
            reason_codes = list(self.decision_status.reason_codes)
            if advisory == LandingDecisionStatus.ABORT:
                decision_mode = "abort"
            elif advisory == LandingDecisionStatus.GO_AROUND:
                decision_mode = "go_around"
            elif advisory == LandingDecisionStatus.HOLD:
                decision_mode = "hold"
            elif advisory == LandingDecisionStatus.REPLAN:
                decision_mode = "replan"
            else:
                decision_mode = "continue"
        return decision_mode, reason_codes

    def target_height_offset(self, phase, active_mode):
        if active_mode in ("abort", "go_around"):
            return float(self.get_parameter("approach_height").value)
        if active_mode == "hold":
            return float(self.get_parameter("synchronize_height").value)
        if phase in (MissionStatus.SEARCH, MissionStatus.APPROACH):
            return float(self.get_parameter("approach_height").value)
        if phase == MissionStatus.ALIGN:
            return float(self.get_parameter("align_height").value)
        if phase in (MissionStatus.SYNCHRONIZE, MissionStatus.WINDOW_WAIT):
            return float(self.get_parameter("synchronize_height").value)
        if phase in (MissionStatus.TERMINAL_DESCENT, MissionStatus.TOUCHDOWN):
            return float(self.get_parameter("terminal_height").value)
        return 0.0

    def build_target_pose(self, backend_name, active_mode):
        if self.zone_state is None or self.mission_status is None:
            return None

        base_pose = (
            copy.deepcopy(self.guidance_reference.target_pose)
            if self.guidance_reference is not None
            else copy.deepcopy(self.zone_state.center_pose)
        )
        base_pose.position.x = self.zone_state.center_pose.position.x
        base_pose.position.y = self.zone_state.center_pose.position.y
        base_pose.position.z = (
            self.zone_state.center_pose.position.z
            + self.target_height_offset(self.mission_status.phase, active_mode)
        )
        base_pose.orientation = copy.deepcopy(self.zone_state.center_pose.orientation)

        if backend_name in (
            "moving_target",
            "chance_constrained",
            "tube_based",
            "learning_augmented",
        ):
            lookahead = float(self.get_parameter("moving_target_lookahead_sec").value)
            base_pose.position.x += self.zone_state.twist.linear.x * lookahead
            base_pose.position.y += self.zone_state.twist.linear.y * lookahead
            base_pose.position.z += self.zone_state.twist.linear.z * lookahead

        return base_pose

    def build_target_twist(self, backend_name, active_mode):
        twist = Twist()
        if self.zone_state is None:
            return twist

        if backend_name in (
            "moving_target",
            "chance_constrained",
            "tube_based",
            "learning_augmented",
        ):
            twist = copy.deepcopy(self.zone_state.twist)

        if active_mode == "hold":
            twist.linear = Vector3()
            twist.angular = Vector3()

        return twist

    def build_terminal_target(self, target_pose, target_twist):
        terminal_target = TerminalTargetSpec()
        terminal_target.header.stamp = self.get_clock().now().to_msg()
        terminal_target.mode = TerminalTargetSpec.MODE_POINT
        terminal_target.target_pose = copy.deepcopy(target_pose)
        terminal_target.target_twist = copy.deepcopy(target_twist)
        terminal_target.touchdown_tolerance_xy = float(
            self.get_parameter("default_terminal_xy_tolerance").value
        )
        terminal_target.touchdown_tolerance_z = float(
            self.get_parameter("default_terminal_z_tolerance").value
        )
        terminal_target.heading_tolerance_rad = float(
            self.get_parameter("default_heading_tolerance_rad").value
        )
        terminal_target.source = "planner"
        return terminal_target

    def build_point(self, pose, twist, time_from_start):
        point = ReferenceTrajectoryPoint()
        point.time_from_start = duration_from_seconds(time_from_start)
        point.pose = copy.deepcopy(pose)
        point.twist = copy.deepcopy(twist)
        point.acceleration = Vector3()
        point.yaw = yaw_from_quaternion(pose.orientation)
        point.yaw_rate = float(twist.angular.z)
        return point

    def normalized_backend(self, requested_backend):
        if requested_backend in (
            "baseline",
            "moving_target",
            "chance_constrained",
            "tube_based",
            "learning_augmented",
        ):
            return requested_backend
        return "baseline"

    def publish_plan(self):
        if self.relative_state is None or self.mission_status is None or self.zone_state is None:
            return

        requested_backend = self.resolve_backend_name()
        backend_name = self.normalized_backend(requested_backend)
        decision_mode, decision_reason_codes = self.determine_mode()
        if decision_mode is None:
            decision_mode = "continue"

        diagnostic_codes = []
        active_constraints = []
        replan_reason_codes = []
        replan_requested = False
        feasible = True

        if backend_name != requested_backend:
            diagnostic_codes.append(f"backend_fallback_{requested_backend}")

        if self.platform_state is None:
            diagnostic_codes.append("degraded_missing_platform_state")
        if self.guidance_reference is None:
            diagnostic_codes.append("degraded_missing_guidance_reference")

        if self.window_logic_enabled():
            active_constraints.append("window_logic_enabled")
            if self.window_status is None:
                diagnostic_codes.append("degraded_missing_window_status")
            elif not self.window_status.window_open:
                active_constraints.append("window_closed")
                if decision_mode in ("continue", "replan"):
                    replan_requested = True
                    replan_reason_codes.append(self.window_status.window_reason or "window_closed")
        else:
            active_constraints.append("window_logic_disabled")

        if decision_mode == "hold":
            active_constraints.append("decision_hold")
        elif decision_mode == "go_around":
            active_constraints.append("decision_go_around")
            replan_requested = True
            replan_reason_codes.extend(decision_reason_codes or ["decision_go_around"])
        elif decision_mode == "abort":
            active_constraints.append("decision_abort")
            replan_requested = True
            replan_reason_codes.extend(decision_reason_codes or ["decision_abort"])
            feasible = False
        elif decision_mode == "replan":
            active_constraints.append("decision_replan")
            replan_requested = True
            replan_reason_codes.extend(decision_reason_codes or ["decision_replan"])

        start_time = perf_counter()
        target_pose = self.build_target_pose(backend_name, decision_mode)
        target_twist = self.build_target_twist(backend_name, decision_mode)
        terminal_target = self.build_terminal_target(target_pose, target_twist)

        horizon = max(0.1, float(self.get_parameter("output_horizon_sec").value))
        dt = max(0.05, float(self.get_parameter("sampling_dt_sec").value))
        step_count = max(1, int(round(horizon / dt)))
        trajectory_points = []
        for index in range(step_count + 1):
            point_pose = copy.deepcopy(target_pose)
            point_twist = copy.deepcopy(target_twist)
            time_from_start = min(horizon, index * dt)
            if backend_name in (
                "moving_target",
                "chance_constrained",
                "tube_based",
                "learning_augmented",
            ):
                point_pose.position.x += self.zone_state.twist.linear.x * time_from_start
                point_pose.position.y += self.zone_state.twist.linear.y * time_from_start
                point_pose.position.z += self.zone_state.twist.linear.z * time_from_start
            trajectory_points.append(self.build_point(point_pose, point_twist, time_from_start))

        solve_time_ms = float((perf_counter() - start_time) * 1000.0)
        self.sequence_id += 1

        reference_msg = ReferenceTrajectory()
        reference_msg.header.stamp = self.get_clock().now().to_msg()
        reference_msg.phase = self.mission_status.phase
        reference_msg.planner_backend = backend_name
        reference_msg.trajectory_points = trajectory_points
        reference_msg.terminal_target = terminal_target
        reference_msg.feasible = feasible
        reference_msg.replan_requested = replan_requested
        reference_msg.replan_reason = ",".join(replan_reason_codes)
        reference_msg.diagnostic_code = ",".join(diagnostic_codes) if diagnostic_codes else "nominal"
        reference_msg.solve_time_ms = solve_time_ms
        reference_msg.valid_horizon = duration_from_seconds(horizon)
        reference_msg.sequence_id = self.sequence_id
        reference_msg.source = "planner"
        self.reference_pub.publish(reference_msg)

        status_msg = PlannerStatus()
        status_msg.header.stamp = reference_msg.header.stamp
        status_msg.phase = self.mission_status.phase
        status_msg.planner_backend = backend_name
        status_msg.feasible = feasible
        status_msg.replan_requested = replan_requested
        status_msg.replan_reason_codes = replan_reason_codes
        status_msg.diagnostic_code = reference_msg.diagnostic_code
        status_msg.solve_time_ms = solve_time_ms
        status_msg.active_terminal_mode = decision_mode
        status_msg.active_constraints = active_constraints
        status_msg.source = "planner"
        self.status_pub.publish(status_msg)


def main():
    rclpy.init()
    node = PlannerFacadeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
