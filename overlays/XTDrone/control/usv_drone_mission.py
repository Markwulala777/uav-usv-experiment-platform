#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, SetMode
from gazebo_msgs.msg import ModelStates
from std_msgs.msg import Float32
import math
from tf.transformations import quaternion_from_euler, euler_from_quaternion

class UsvDroneMission:
    def __init__(self):
        rospy.init_node('usv_drone_mission', anonymous=True)

        self.state = State()
        self.wamv_pose = None
        self.drone_pose = None
        self.local_pose = None
        self.commanded_z = None # 保存上一次期望的高以平滑下降
        
        # MAVROS 客户端
        self.local_pos_pub = rospy.Publisher('/iris_0/mavros/setpoint_position/local', PoseStamped, queue_size=10)
        self.arming_client = rospy.ServiceProxy('iris_0/mavros/cmd/arming', CommandBool)
        self.set_mode_client = rospy.ServiceProxy('iris_0/mavros/set_mode', SetMode)
        rospy.Subscriber('/iris_0/mavros/state', State, self.state_cb)
        rospy.Subscriber('/iris_0/mavros/local_position/pose', PoseStamped, self.local_pose_cb)

        # Gazebo 状态
        rospy.Subscriber("/gazebo/model_states", ModelStates, self.states_cb, queue_size=10)
        
        # 无人船控制
        self.pub_left_thrust = rospy.Publisher('/wamv/thrusters/left_thrust_cmd', Float32, queue_size=1)
        self.pub_right_thrust = rospy.Publisher('/wamv/thrusters/right_thrust_cmd', Float32, queue_size=1)
        self.pub_left_thrust_angle = rospy.Publisher('/wamv/thrusters/left_thrust_angle', Float32, queue_size=1)
        self.pub_right_thrust_angle = rospy.Publisher('/wamv/thrusters/right_thrust_angle', Float32, queue_size=1)

        self.rate = rospy.Rate(20.0)

        # 参数
        self.takeoff_height = 5
        self.usv_thrust = 50.0
        self.catch_distance = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.offset_z = 0.0
        
        self.takeoff_x = 0.0
        self.takeoff_y = 0.0

    def state_cb(self, msg):
        self.state = msg

    def local_pose_cb(self, msg):
        self.local_pose = msg

    def states_cb(self, msg):
        try:
            if "wamv" in msg.name:
                self.wamv_pose = msg.pose[msg.name.index('wamv')]
            if "iris_0" in msg.name:
                self.drone_pose = msg.pose[msg.name.index('iris_0')]
        except ValueError:
            pass

    def publish_usv_cmd(self, thrust):
        self.pub_left_thrust.publish(Float32(thrust))
        self.pub_right_thrust.publish(Float32(thrust))
        self.pub_left_thrust_angle.publish(Float32(0.0))
        self.pub_right_thrust_angle.publish(Float32(0.0))

    def publish_pose_setpoint(self, x, y, z):
        pose = PoseStamped()
        pose.header.stamp = rospy.Time.now()
        pose.header.frame_id = "map"
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = z
        
        q = quaternion_from_euler(0, 0, 0)
        pose.pose.orientation.x = q[0]
        pose.pose.orientation.y = q[1]
        pose.pose.orientation.z = q[2]
        pose.pose.orientation.w = q[3]
        
        self.local_pos_pub.publish(pose)

    def run(self):
        # 1. 等待连接
        rospy.loginfo("Waiting for MAVROS connection...")
        while not rospy.is_shutdown() and not self.state.connected:
            self.rate.sleep()
        rospy.loginfo("MAVROS connected.")
            
        rospy.loginfo("Waiting for Gazebo models...")
        while not rospy.is_shutdown() and (self.wamv_pose is None or self.drone_pose is None):
            self.rate.sleep()
        rospy.loginfo("Gazebo models found.")
        
        rospy.loginfo("Waiting for Local Pose...")
        while not rospy.is_shutdown() and self.local_pose is None:
            self.rate.sleep()
        rospy.loginfo("Local Pose received.")
            
        # 记录初始位置
        self.offset_x = self.drone_pose.position.x
        self.offset_y = self.drone_pose.position.y
        self.offset_z = self.drone_pose.position.z
        
        self.takeoff_x = self.local_pose.pose.position.x
        self.takeoff_y = self.local_pose.pose.position.y
        
        rospy.loginfo("Home Position (Gazebo): x={:.2f}, y={:.2f}".format(self.offset_x, self.offset_y))
        rospy.loginfo("Home Position (Local): x={:.2f}, y={:.2f}".format(self.takeoff_x, self.takeoff_y))
        
        mission_state = 0 
        start_time = rospy.Time.now()
        last_req = rospy.Time.now()
        
        rospy.loginfo("Mission Start: USV moving...")

        while not rospy.is_shutdown():
            current_time = rospy.Time.now()
            elapsed = (current_time - start_time).to_sec()
            
            # 状态 0: 船先走 5 秒，飞机原地待命
            if mission_state == 0:
                self.publish_usv_cmd(self.usv_thrust)
                self.publish_pose_setpoint(self.takeoff_x, self.takeoff_y, self.local_pose.pose.position.z)
                
                if elapsed > 5.0:
                    mission_state = 1
                    rospy.loginfo("5s Elapsed. Switching to Takeoff.")
                    last_req = current_time - rospy.Duration(10) 

            # 状态 1: 飞机起飞
            elif mission_state == 1:
                self.publish_usv_cmd(self.usv_thrust)
                self.publish_pose_setpoint(self.takeoff_x, self.takeoff_y, self.takeoff_height)
                
                if self.state.mode != "OFFBOARD" and (current_time - last_req) > rospy.Duration(2.0):
                    rospy.loginfo("Requesting OFFBOARD...")
                    try:
                        resp = self.set_mode_client(custom_mode="OFFBOARD")
                        if resp.mode_sent:
                            rospy.loginfo("OFFBOARD enabled")
                    except rospy.ServiceException as e:
                        rospy.logwarn(e)
                    last_req = current_time
                    
                elif not self.state.armed and (current_time - last_req) > rospy.Duration(2.0):
                    rospy.loginfo("Requesting ARM...")
                    try:
                        resp = self.arming_client(True)
                        if resp.success:
                            rospy.loginfo("Vehicle armed")
                    except rospy.ServiceException as e:
                        rospy.logwarn(e)
                    last_req = current_time
                
                if self.state.mode == "OFFBOARD" and self.state.armed:
                     if self.local_pose.pose.position.z > (self.takeoff_height - 0.3):
                        mission_state = 2
                        rospy.loginfo("Takeoff Done. Chasing.")

            # 状态 2: 飞机追船
            elif mission_state == 2:
                self.publish_usv_cmd(self.usv_thrust)
                
                # 计算相对位置: Target_Local = Target_Global - Home_Global + Home_Local
                # 增加前向偏移 (前进方向)
                q = self.wamv_pose.orientation
                (_, _, yaw_usv) = euler_from_quaternion([q.x, q.y, q.z, q.w])
                fwd_offset = 0.5
                
                target_x_global = self.wamv_pose.position.x + fwd_offset * math.cos(yaw_usv)
                target_y_global = self.wamv_pose.position.y + fwd_offset * math.sin(yaw_usv)

                target_x = target_x_global - self.offset_x + self.takeoff_x
                target_y = target_y_global - self.offset_y + self.takeoff_y
                
                self.publish_pose_setpoint(target_x, target_y, self.takeoff_height)
                
                dx = self.drone_pose.position.x - self.wamv_pose.position.x
                dy = self.drone_pose.position.y - self.wamv_pose.position.y
                dist = math.hypot(dx, dy)
                
                rospy.loginfo_throttle(1, "Chasing USV... Distance: {:.2f}m".format(dist))

                if dist < 3: # 增大判定范围
                    mission_state = 3
                    rospy.loginfo("Caught up! Landing.")
                    last_req = current_time - rospy.Duration(10)

            # 状态 3: 降落
            elif mission_state == 3:
                self.publish_usv_cmd(0.0) # 停止无人船

                # 更新目标位置 (含前向偏移)
                q = self.wamv_pose.orientation
                (_, _, yaw_usv) = euler_from_quaternion([q.x, q.y, q.z, q.w])
                fwd_offset = 0.5
                
                target_x_global = self.wamv_pose.position.x + fwd_offset * math.cos(yaw_usv)
                target_y_global = self.wamv_pose.position.y + fwd_offset * math.sin(yaw_usv)
                
                target_x = target_x_global - self.offset_x + self.takeoff_x
                target_y = target_y_global - self.offset_y + self.takeoff_y
                
                # 不切入 AUTO.LAND，而是继续发送位置点，但是把 Z 轴设定点逐步降低
                # 这样可以保持在 XY 点上方垂直下降，而不是斜着进入 AUTO.LAND 设定的原点
                if self.commanded_z is None:
                    self.commanded_z = self.local_pose.pose.position.z
                    
                self.commanded_z -= 0.5 / 20.0 # 0.5m/s rate at 20Hz
                self.commanded_z = max(-0.5, self.commanded_z) # allow slightly below zero to force touching deck
                
                self.publish_pose_setpoint(target_x, target_y, self.commanded_z)
                
                # 降落判定：如果高度低于 2 米且基本静止，视为降落完成，发送上锁指令
                if self.local_pose.pose.position.z < 2.0:
                    if (current_time - last_req) > rospy.Duration(2.0):
                        try:
                            resp = self.arming_client(False)
                            if resp.success:
                                rospy.loginfo("Disarmed successfully.")
                                mission_state = 4
                        except rospy.ServiceException as e:
                            rospy.logwarn(e)
                        last_req = current_time
                
            elif mission_state == 4:
                break
                
            self.rate.sleep()

if __name__ == '__main__':
    try:
        mission = UsvDroneMission()
        mission.run()
    except rospy.ROSInterruptException:
        pass
