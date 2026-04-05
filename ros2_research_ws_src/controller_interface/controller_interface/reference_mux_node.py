from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import (
    ControllerReference,
    GuidanceReference,
    ReferenceTrajectory,
    ScenarioProfile,
)


class ReferenceMuxNode(Node):
    def __init__(self):
        super().__init__("reference_mux")

        self.guidance_reference = None
        self.trajectory_reference = None
        self.scenario_profile = None
        self.sequence_id = 0

        self.declare_parameter("source_mode", "")
        self.declare_parameter("reference_source", "scenario_default")

        self.reference_pub = self.create_publisher(
            ControllerReference, "/controller/reference_active", 10
        )

        self.create_subscription(GuidanceReference, "/guidance/reference", self.guidance_cb, 10)
        self.create_subscription(
            ReferenceTrajectory, "/planner/reference_trajectory", self.trajectory_cb, 10
        )
        self.create_subscription(
            ScenarioProfile, "/experiment/scenario_profile", self.scenario_profile_cb, 10
        )

        self.timer = self.create_timer(0.05, self.publish_reference)
        self.get_logger().info("controller_interface reference mux is running.")

    def guidance_cb(self, msg):
        self.guidance_reference = msg

    def trajectory_cb(self, msg):
        self.trajectory_reference = msg

    def scenario_profile_cb(self, msg):
        self.scenario_profile = msg

    def resolve_reference_source(self):
        explicit_source = str(self.get_parameter("reference_source").value).strip().lower()
        if explicit_source not in ("", "scenario_default", "auto"):
            return explicit_source

        legacy_source = str(self.get_parameter("source_mode").value).strip().lower()
        if legacy_source:
            return legacy_source

        if self.scenario_profile is not None:
            return self.scenario_profile.default_reference_source.strip().lower() or "guidance"

        return "guidance"

    def planner_allowed_active_path(self):
        if self.scenario_profile is None:
            return True
        return bool(self.scenario_profile.allow_planner_active_path) and not bool(
            self.scenario_profile.planner_shadow_mode
        )

    def planner_terminal_spec(self, trajectory_reference):
        if trajectory_reference.terminal_target.mode == trajectory_reference.terminal_target.MODE_SET_SUMMARY:
            return "terminal_set_summary"
        if trajectory_reference.terminal_target.mode == trajectory_reference.terminal_target.MODE_POINT:
            return "terminal_point"
        return "terminal_unspecified"

    def publish_reference(self):
        preferred_source = self.resolve_reference_source()
        planner_active = preferred_source == "planner" and self.planner_allowed_active_path()

        if planner_active:
            if self.trajectory_reference is None:
                return
            msg = ControllerReference()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.source_type = ControllerReference.SOURCE_TRAJECTORY
            msg.phase = self.trajectory_reference.phase
            if self.trajectory_reference.trajectory_points:
                first_point = self.trajectory_reference.trajectory_points[0]
                msg.target_pose = first_point.pose
                msg.target_twist = first_point.twist
            else:
                msg.target_twist = Twist()
            msg.terminal_spec = self.planner_terminal_spec(self.trajectory_reference)
            msg.feasible = self.trajectory_reference.feasible
            msg.sequence_id = self.trajectory_reference.sequence_id
            msg.source = "planner"
            self.reference_pub.publish(msg)
            return

        if self.guidance_reference is None:
            return

        msg = ControllerReference()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.source_type = ControllerReference.SOURCE_GUIDANCE
        msg.phase = self.guidance_reference.phase
        msg.target_pose = self.guidance_reference.target_pose
        msg.target_twist.linear.x = self.guidance_reference.target_velocity_envelope.x
        msg.target_twist.linear.y = self.guidance_reference.target_velocity_envelope.y
        msg.target_twist.linear.z = self.guidance_reference.target_velocity_envelope.z
        msg.terminal_spec = "guidance_reference"
        msg.feasible = True
        self.sequence_id += 1
        msg.sequence_id = self.sequence_id
        msg.source = "guidance"
        self.reference_pub.publish(msg)


def main():
    rclpy.init()
    node = ReferenceMuxNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
