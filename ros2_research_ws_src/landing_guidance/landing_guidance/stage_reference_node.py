import copy

import rclpy
from rclpy.node import Node
from mission_stack_msgs.msg import GuidanceReference, LandingZoneState, MissionStatus, RelativeState


class StageReferenceNode(Node):
    def __init__(self):
        super().__init__("stage_reference")

        self.mission_status = None
        self.zone_state = None
        self.relative_state = None

        self.declare_parameter("approach_height", 5.0)
        self.declare_parameter("align_height", 3.0)
        self.declare_parameter("synchronize_height", 2.0)
        self.declare_parameter("terminal_height", 0.3)
        self.declare_parameter("descent_rate", 0.4)

        self.reference_pub = self.create_publisher(GuidanceReference, "/guidance/reference", 10)

        self.create_subscription(MissionStatus, "/mission/phase", self.mission_status_cb, 10)
        self.create_subscription(
            LandingZoneState, "/platform/landing_zone_state", self.zone_state_cb, 10
        )
        self.create_subscription(RelativeState, "/relative_state/active", self.relative_state_cb, 10)

        self.timer = self.create_timer(0.05, self.publish_reference)
        self.get_logger().info("landing_guidance stage-reference node is running.")

    def mission_status_cb(self, msg):
        self.mission_status = msg

    def zone_state_cb(self, msg):
        self.zone_state = msg

    def relative_state_cb(self, msg):
        self.relative_state = msg

    def publish_reference(self):
        if self.mission_status is None or self.zone_state is None:
            return

        approach_height = float(self.get_parameter("approach_height").value)
        align_height = float(self.get_parameter("align_height").value)
        synchronize_height = float(self.get_parameter("synchronize_height").value)
        terminal_height = float(self.get_parameter("terminal_height").value)
        descent_rate = float(self.get_parameter("descent_rate").value)

        target_pose = copy.deepcopy(self.zone_state.center_pose)
        target_pose.position.z += approach_height
        velocity_envelope = (0.8, 0.8, 0.4)

        if self.mission_status.phase == MissionStatus.ALIGN:
            target_pose.position.z = self.zone_state.center_pose.position.z + align_height
            velocity_envelope = (0.6, 0.6, 0.3)
        elif self.mission_status.phase in (MissionStatus.SYNCHRONIZE, MissionStatus.WINDOW_WAIT):
            target_pose.position.z = self.zone_state.center_pose.position.z + synchronize_height
            velocity_envelope = (0.4, 0.4, 0.2)
        elif self.mission_status.phase in (MissionStatus.TERMINAL_DESCENT, MissionStatus.TOUCHDOWN):
            target_pose.position.z = self.zone_state.center_pose.position.z + terminal_height
            velocity_envelope = (0.3, 0.3, descent_rate)
        elif self.mission_status.phase == MissionStatus.POST_LANDING:
            target_pose.position.z = self.zone_state.center_pose.position.z
            velocity_envelope = (0.0, 0.0, 0.0)

        msg = GuidanceReference()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.phase = self.mission_status.phase
        msg.target_pose = target_pose
        msg.target_velocity_envelope.x = float(velocity_envelope[0])
        msg.target_velocity_envelope.y = float(velocity_envelope[1])
        msg.target_velocity_envelope.z = float(velocity_envelope[2])
        msg.corridor_reference = self.zone_state.zone_pose
        msg.descent_rate = descent_rate
        msg.source = "landing_guidance"
        self.reference_pub.publish(msg)


def main():
    rclpy.init()
    node = StageReferenceNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
