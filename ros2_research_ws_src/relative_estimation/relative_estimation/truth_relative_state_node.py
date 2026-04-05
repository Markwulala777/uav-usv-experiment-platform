import math

import rclpy
from geometry_msgs.msg import PoseStamped, TwistStamped
from rclpy.node import Node
from mission_stack_msgs.msg import LandingZoneState, RelativeState, UavState


def quat_conjugate(q):
    return [-q[0], -q[1], -q[2], q[3]]


def quat_multiply(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return [
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    ]


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


class TruthRelativeStateNode(Node):
    def __init__(self):
        super().__init__("truth_relative_state")
        self.zone_state = None
        self.uav_state = None

        self.relative_state_pub = self.create_publisher(RelativeState, "/relative_state/truth", 10)
        self.relative_pose_debug_pub = self.create_publisher(
            PoseStamped, "/relative_estimation/debug/relative_pose", 10
        )
        self.relative_twist_debug_pub = self.create_publisher(
            TwistStamped, "/relative_estimation/debug/relative_twist", 10
        )

        self.create_subscription(
            LandingZoneState, "/platform/landing_zone_state", self.zone_state_cb, 10
        )
        self.create_subscription(UavState, "/uav/state_truth", self.uav_state_cb, 10)

        self.timer = self.create_timer(0.05, self.publish_relative_state)
        self.get_logger().info("relative_estimation truth node is running.")

    def zone_state_cb(self, msg):
        self.zone_state = msg

    def uav_state_cb(self, msg):
        self.uav_state = msg

    def publish_relative_state(self):
        if self.zone_state is None or self.uav_state is None:
            return

        target_q = [
            self.zone_state.center_pose.orientation.x,
            self.zone_state.center_pose.orientation.y,
            self.zone_state.center_pose.orientation.z,
            self.zone_state.center_pose.orientation.w,
        ]
        target_q_inv = quat_conjugate(target_q)
        uav_q = [
            self.uav_state.pose.orientation.x,
            self.uav_state.pose.orientation.y,
            self.uav_state.pose.orientation.z,
            self.uav_state.pose.orientation.w,
        ]

        relative_position_world = [
            self.uav_state.pose.position.x - self.zone_state.center_pose.position.x,
            self.uav_state.pose.position.y - self.zone_state.center_pose.position.y,
            self.uav_state.pose.position.z - self.zone_state.center_pose.position.z,
        ]
        relative_linear_world = [
            self.uav_state.twist.linear.x - self.zone_state.twist.linear.x,
            self.uav_state.twist.linear.y - self.zone_state.twist.linear.y,
            self.uav_state.twist.linear.z - self.zone_state.twist.linear.z,
        ]
        relative_angular_world = [
            self.uav_state.twist.angular.x - self.zone_state.twist.angular.x,
            self.uav_state.twist.angular.y - self.zone_state.twist.angular.y,
            self.uav_state.twist.angular.z - self.zone_state.twist.angular.z,
        ]

        relative_position_target = rotate_vector(target_q_inv, relative_position_world)
        relative_linear_target = rotate_vector(target_q_inv, relative_linear_world)
        relative_angular_target = rotate_vector(target_q_inv, relative_angular_world)
        relative_q = quat_multiply(target_q_inv, uav_q)

        state_msg = RelativeState()
        state_msg.header = self.uav_state.header
        state_msg.source_mode = "truth"
        state_msg.position.x = relative_position_target[0]
        state_msg.position.y = relative_position_target[1]
        state_msg.position.z = relative_position_target[2]
        state_msg.linear_velocity.x = relative_linear_target[0]
        state_msg.linear_velocity.y = relative_linear_target[1]
        state_msg.linear_velocity.z = relative_linear_target[2]
        state_msg.angular_velocity.x = relative_angular_target[0]
        state_msg.angular_velocity.y = relative_angular_target[1]
        state_msg.angular_velocity.z = relative_angular_target[2]
        state_msg.attitude_error.x = relative_q[0]
        state_msg.attitude_error.y = relative_q[1]
        state_msg.attitude_error.z = relative_q[2]
        state_msg.attitude_error.w = relative_q[3]

        pose_msg = PoseStamped()
        pose_msg.header.stamp = self.uav_state.header.stamp
        pose_msg.header.frame_id = "landing_target_frame"
        pose_msg.pose.position.x = state_msg.position.x
        pose_msg.pose.position.y = state_msg.position.y
        pose_msg.pose.position.z = state_msg.position.z
        pose_msg.pose.orientation = state_msg.attitude_error

        twist_msg = TwistStamped()
        twist_msg.header.stamp = self.uav_state.header.stamp
        twist_msg.header.frame_id = "landing_target_frame"
        twist_msg.twist.linear.x = state_msg.linear_velocity.x
        twist_msg.twist.linear.y = state_msg.linear_velocity.y
        twist_msg.twist.linear.z = state_msg.linear_velocity.z
        twist_msg.twist.angular.x = state_msg.angular_velocity.x
        twist_msg.twist.angular.y = state_msg.angular_velocity.y
        twist_msg.twist.angular.z = state_msg.angular_velocity.z

        self.relative_state_pub.publish(state_msg)
        self.relative_pose_debug_pub.publish(pose_msg)
        self.relative_twist_debug_pub.publish(twist_msg)


def main():
    rclpy.init()
    node = TruthRelativeStateNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
