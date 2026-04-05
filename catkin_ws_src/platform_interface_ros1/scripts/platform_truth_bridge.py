#!/usr/bin/env python3

import math

import rospy
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import PoseStamped, TwistStamped
from tf.transformations import quaternion_conjugate, quaternion_matrix, quaternion_multiply


def rotate_vector(quaternion, vector):
    matrix = quaternion_matrix(quaternion)
    return [
        matrix[0][0] * vector[0] + matrix[0][1] * vector[1] + matrix[0][2] * vector[2],
        matrix[1][0] * vector[0] + matrix[1][1] * vector[1] + matrix[1][2] * vector[2],
        matrix[2][0] * vector[0] + matrix[2][1] * vector[1] + matrix[2][2] * vector[2],
    ]


class PlatformTruthBridge:
    def __init__(self):
        self.world_frame = rospy.get_param("~world_frame", "world")
        self.deck_frame = rospy.get_param("~deck_frame", "deck_frame")
        self.landing_target_frame = rospy.get_param("~landing_target_frame", "landing_target_frame")
        self.uav_frame = rospy.get_param("~uav_frame", "uav_base_link")
        self.platform_mode = rospy.get_param("~platform_mode", "maritime_usv")
        self.platform_model = rospy.get_param(
            "~platform_model", rospy.get_param("~wamv_model", "wamv")
        )
        self.uav_model = rospy.get_param("~uav_model", "iris_0")
        self.platform_offset = rospy.get_param(
            "~platform_offset_xyz", rospy.get_param("~deck_offset_xyz", [0.0, 0.0, 1.25])
        )
        self.target_offset = rospy.get_param(
            "~landing_zone_offset_xyz",
            rospy.get_param("~landing_target_offset_xyz", [0.5, 0.0, 1.25]),
        )

        self.deck_pose_pub = rospy.Publisher("/bridge/deck/truth/pose", PoseStamped, queue_size=10)
        self.deck_twist_pub = rospy.Publisher("/bridge/deck/truth/twist", TwistStamped, queue_size=10)
        self.target_pose_pub = rospy.Publisher("/bridge/landing_target/truth/pose", PoseStamped, queue_size=10)
        self.target_twist_pub = rospy.Publisher("/bridge/landing_target/truth/twist", TwistStamped, queue_size=10)
        self.uav_pose_pub = rospy.Publisher("/bridge/uav/truth/pose", PoseStamped, queue_size=10)
        self.uav_twist_pub = rospy.Publisher("/bridge/uav/truth/twist", TwistStamped, queue_size=10)
        self.relative_pose_pub = rospy.Publisher("/bridge/relative/truth/pose", PoseStamped, queue_size=10)
        self.relative_twist_pub = rospy.Publisher("/bridge/relative/truth/twist", TwistStamped, queue_size=10)

        rospy.Subscriber("/gazebo/model_states", ModelStates, self.model_states_cb, queue_size=10)
        rospy.loginfo(
            "platform_interface_ros1 started. mode=%s platform_model=%s uav_model=%s. Waiting for /gazebo/model_states.",
            self.platform_mode,
            self.platform_model,
            self.uav_model,
        )

    def build_pose(self, stamp, frame_id, position, orientation):
        msg = PoseStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        msg.pose.position.x = position[0]
        msg.pose.position.y = position[1]
        msg.pose.position.z = position[2]
        msg.pose.orientation.x = orientation[0]
        msg.pose.orientation.y = orientation[1]
        msg.pose.orientation.z = orientation[2]
        msg.pose.orientation.w = orientation[3]
        return msg

    def build_twist(self, stamp, frame_id, linear, angular):
        msg = TwistStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        msg.twist.linear.x = linear[0]
        msg.twist.linear.y = linear[1]
        msg.twist.linear.z = linear[2]
        msg.twist.angular.x = angular[0]
        msg.twist.angular.y = angular[1]
        msg.twist.angular.z = angular[2]
        return msg

    def apply_offset(self, pose, offset_xyz):
        quaternion = [
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        ]
        rotated_offset = rotate_vector(quaternion, offset_xyz)
        return [
            pose.position.x + rotated_offset[0],
            pose.position.y + rotated_offset[1],
            pose.position.z + rotated_offset[2],
        ], quaternion

    def relative_orientation(self, target_quaternion, uav_quaternion):
        target_inverse = quaternion_conjugate(target_quaternion)
        return quaternion_multiply(target_inverse, uav_quaternion)

    def rotate_into_target_frame(self, target_quaternion, vector):
        target_inverse = quaternion_conjugate(target_quaternion)
        return rotate_vector(target_inverse, vector)

    def platform_twist_vectors(self, platform_twist):
        if self.platform_mode == "static_pad":
            zero = [0.0, 0.0, 0.0]
            return zero, zero

        return (
            [platform_twist.linear.x, platform_twist.linear.y, platform_twist.linear.z],
            [platform_twist.angular.x, platform_twist.angular.y, platform_twist.angular.z],
        )

    def model_states_cb(self, msg):
        try:
            platform_idx = msg.name.index(self.platform_model)
            uav_idx = msg.name.index(self.uav_model)
        except ValueError:
            rospy.logwarn_throttle(
                5.0,
                "platform_interface_ros1 could not find models '%s' and '%s'.",
                self.platform_model,
                self.uav_model,
            )
            return

        platform_pose = msg.pose[platform_idx]
        platform_twist = msg.twist[platform_idx]
        uav_pose = msg.pose[uav_idx]
        uav_twist = msg.twist[uav_idx]

        stamp = rospy.Time.now()

        deck_position, deck_quaternion = self.apply_offset(platform_pose, self.platform_offset)
        target_position, target_quaternion = self.apply_offset(platform_pose, self.target_offset)
        platform_twist_linear, platform_twist_angular = self.platform_twist_vectors(platform_twist)
        target_twist_linear = list(platform_twist_linear)
        target_twist_angular = list(platform_twist_angular)
        uav_position = [uav_pose.position.x, uav_pose.position.y, uav_pose.position.z]
        uav_quaternion = [uav_pose.orientation.x, uav_pose.orientation.y, uav_pose.orientation.z, uav_pose.orientation.w]

        relative_position_world = [
            uav_position[0] - target_position[0],
            uav_position[1] - target_position[1],
            uav_position[2] - target_position[2],
        ]
        relative_linear_world = [
            uav_twist.linear.x - target_twist_linear[0],
            uav_twist.linear.y - target_twist_linear[1],
            uav_twist.linear.z - target_twist_linear[2],
        ]
        relative_angular_world = [
            uav_twist.angular.x - target_twist_angular[0],
            uav_twist.angular.y - target_twist_angular[1],
            uav_twist.angular.z - target_twist_angular[2],
        ]

        relative_position_target = self.rotate_into_target_frame(target_quaternion, relative_position_world)
        relative_linear_target = self.rotate_into_target_frame(target_quaternion, relative_linear_world)
        relative_angular_target = self.rotate_into_target_frame(target_quaternion, relative_angular_world)
        relative_quaternion = self.relative_orientation(target_quaternion, uav_quaternion)

        self.deck_pose_pub.publish(self.build_pose(stamp, self.world_frame, deck_position, deck_quaternion))
        self.deck_twist_pub.publish(
            self.build_twist(
                stamp,
                self.world_frame,
                platform_twist_linear,
                platform_twist_angular,
            )
        )
        self.target_pose_pub.publish(self.build_pose(stamp, self.world_frame, target_position, target_quaternion))
        self.target_twist_pub.publish(
            self.build_twist(
                stamp,
                self.world_frame,
                target_twist_linear,
                target_twist_angular,
            )
        )
        self.uav_pose_pub.publish(self.build_pose(stamp, self.world_frame, uav_position, uav_quaternion))
        self.uav_twist_pub.publish(
            self.build_twist(
                stamp,
                self.world_frame,
                [uav_twist.linear.x, uav_twist.linear.y, uav_twist.linear.z],
                [uav_twist.angular.x, uav_twist.angular.y, uav_twist.angular.z],
            )
        )
        self.relative_pose_pub.publish(self.build_pose(stamp, self.landing_target_frame, relative_position_target, relative_quaternion))
        self.relative_twist_pub.publish(self.build_twist(stamp, self.landing_target_frame, relative_linear_target, relative_angular_target))


def main():
    rospy.init_node("platform_truth_bridge")
    PlatformTruthBridge()
    rospy.spin()


if __name__ == "__main__":
    main()
