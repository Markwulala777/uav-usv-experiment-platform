import math

from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand, VehicleLocalPosition
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool
from mission_stack_msgs.msg import ControllerCommand, MissionStatus, UavState


def yaw_from_quaternion(quaternion):
    siny_cosp = 2.0 * (quaternion.w * quaternion.z + quaternion.x * quaternion.y)
    cosy_cosp = 1.0 - 2.0 * (quaternion.y * quaternion.y + quaternion.z * quaternion.z)
    return math.atan2(siny_cosp, cosy_cosp)


def enu_xyz_to_ned(x, y, z):
    return [y, x, -z]


def ned_position_to_enu(position):
    return [position[1], position[0], -position[2]]


def enu_yaw_to_ned(yaw_enu):
    return math.pi / 2.0 - yaw_enu


class Px4OffboardBridgeNode(Node):
    def __init__(self):
        super().__init__("px4_offboard_bridge")

        self.command = None
        self.abort_requested = False
        self.phase = MissionStatus.SEARCH
        self.setpoint_counter = 0
        self.offboard_requested = False
        self.arm_requested = False
        self.abort_command_sent = False
        self.uav_world_state = None
        self.vehicle_local_position = None
        self.local_origin_world_enu = None
        self.local_origin_resolved = False
        self.last_position_reset_signature = None
        self.last_valid_position_ned = None
        self.last_valid_yaw_ned = None

        self.declare_parameter("fmu_prefix", "/fmu")
        self.declare_parameter("publish_rate_hz", 20.0)
        self.declare_parameter("warmup_setpoints", 20)
        self.declare_parameter("auto_arm", True)
        self.declare_parameter("auto_offboard", True)

        fmu_prefix = str(self.get_parameter("fmu_prefix").value).rstrip("/")
        publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        px4_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.offboard_mode_pub = self.create_publisher(
            OffboardControlMode, f"{fmu_prefix}/in/offboard_control_mode", px4_qos
        )
        self.trajectory_setpoint_pub = self.create_publisher(
            TrajectorySetpoint, f"{fmu_prefix}/in/trajectory_setpoint", px4_qos
        )
        self.vehicle_command_pub = self.create_publisher(
            VehicleCommand, f"{fmu_prefix}/in/vehicle_command", px4_qos
        )

        self.create_subscription(ControllerCommand, "/controller/command", self.command_cb, 10)
        self.create_subscription(UavState, "/uav/state_truth", self.uav_world_state_cb, 10)
        self.create_subscription(Bool, "/safety/abort_request", self.abort_requested_cb, 10)
        self.create_subscription(MissionStatus, "/mission/phase", self.phase_cb, 10)
        self.create_subscription(
            VehicleLocalPosition,
            f"{fmu_prefix}/out/vehicle_local_position",
            self.vehicle_local_position_cb,
            px4_qos,
        )

        self.timer = self.create_timer(1.0 / publish_rate_hz, self.publish_cycle)
        self.get_logger().info("controller_interface PX4 offboard bridge is running.")

    def command_cb(self, msg):
        self.command = msg

    def uav_world_state_cb(self, msg):
        self.uav_world_state = msg
        self.try_resolve_local_origin()

    def abort_requested_cb(self, msg):
        self.abort_requested = msg.data

    def phase_cb(self, msg):
        self.phase = msg.phase

    def vehicle_local_position_cb(self, msg):
        self.vehicle_local_position = msg
        reset_signature = (int(msg.xy_reset_counter), int(msg.z_reset_counter))
        if self.last_position_reset_signature is None:
            self.last_position_reset_signature = reset_signature
        elif reset_signature != self.last_position_reset_signature:
            self.last_position_reset_signature = reset_signature
            self.local_origin_resolved = False
            self.local_origin_world_enu = None
            self.get_logger().warn("PX4 local position reset detected. Recomputing local origin.")

        self.try_resolve_local_origin()

    def now_us(self):
        return int(self.get_clock().now().nanoseconds / 1000)

    def publish_vehicle_command(self, command, param1=0.0, param2=0.0):
        msg = VehicleCommand()
        msg.timestamp = self.now_us()
        msg.param1 = float(param1)
        msg.param2 = float(param2)
        msg.command = command
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        self.vehicle_command_pub.publish(msg)

    def try_resolve_local_origin(self):
        if self.local_origin_resolved:
            return

        if self.uav_world_state is None or self.vehicle_local_position is None:
            return

        if not self.vehicle_local_position.xy_valid or not self.vehicle_local_position.z_valid:
            return

        local_enu = ned_position_to_enu(
            [
                float(self.vehicle_local_position.x),
                float(self.vehicle_local_position.y),
                float(self.vehicle_local_position.z),
            ]
        )
        self.local_origin_world_enu = [
            float(self.uav_world_state.pose.position.x) - local_enu[0],
            float(self.uav_world_state.pose.position.y) - local_enu[1],
            float(self.uav_world_state.pose.position.z) - local_enu[2],
        ]
        self.local_origin_resolved = True

    def world_enu_to_local_enu(self, position):
        return [
            float(position.x) - self.local_origin_world_enu[0],
            float(position.y) - self.local_origin_world_enu[1],
            float(position.z) - self.local_origin_world_enu[2],
        ]

    def publish_cycle(self):
        if self.command is None or self.command.control_mode != ControllerCommand.MODE_POSITION:
            return

        timestamp = self.now_us()
        position_ned = None
        yaw_ned = None

        if self.local_origin_resolved:
            yaw_enu = yaw_from_quaternion(self.command.position_setpoint.orientation)
            local_enu = self.world_enu_to_local_enu(self.command.position_setpoint.position)
            position_ned = enu_xyz_to_ned(local_enu[0], local_enu[1], local_enu[2])
            yaw_ned = enu_yaw_to_ned(yaw_enu)
            self.last_valid_position_ned = list(position_ned)
            self.last_valid_yaw_ned = float(yaw_ned)
        elif self.last_valid_position_ned is not None and self.last_valid_yaw_ned is not None:
            position_ned = list(self.last_valid_position_ned)
            yaw_ned = float(self.last_valid_yaw_ned)
        else:
            return

        offboard_msg = OffboardControlMode()
        offboard_msg.timestamp = timestamp
        offboard_msg.position = True

        trajectory_msg = TrajectorySetpoint()
        trajectory_msg.timestamp = timestamp
        trajectory_msg.position = position_ned
        trajectory_msg.velocity = [math.nan, math.nan, math.nan]
        trajectory_msg.acceleration = [math.nan, math.nan, math.nan]
        trajectory_msg.yaw = yaw_ned

        self.offboard_mode_pub.publish(offboard_msg)
        self.trajectory_setpoint_pub.publish(trajectory_msg)
        self.setpoint_counter += 1

        warmup_setpoints = int(self.get_parameter("warmup_setpoints").value)
        auto_offboard = bool(self.get_parameter("auto_offboard").value)
        auto_arm = bool(self.get_parameter("auto_arm").value)

        if auto_offboard and not self.offboard_requested and self.setpoint_counter >= warmup_setpoints:
            self.publish_vehicle_command(
                VehicleCommand.VEHICLE_CMD_DO_SET_MODE,
                param1=1.0,
                param2=6.0,
            )
            self.offboard_requested = True

        if auto_arm and self.offboard_requested and not self.arm_requested:
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)
            self.arm_requested = True

        if self.abort_requested and not self.abort_command_sent:
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
            self.abort_command_sent = True


def main():
    rclpy.init()
    node = Px4OffboardBridgeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
