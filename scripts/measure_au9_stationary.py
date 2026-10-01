#!/usr/bin/env python3
"""Read-only stationary AU9 sampling; never publishes control commands."""
import argparse
import json
import math
import time
from pathlib import Path

import rclpy
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import JointState, LaserScan
from tf2_msgs.msg import TFMessage
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from tf2_ros import Buffer, TransformListener
from rosgraph_msgs.msg import Clock


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--settle', type=float, default=0)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('au9_stationary_measurement')
    latest = {}
    observations = {}
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)

    def odom(msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        latest['odom'] = [p.x, p.y, yaw]
        latest['velocity'] = [msg.twist.twist.linear.x, msg.twist.twist.linear.y, msg.twist.twist.angular.z]

    def tf(msg):
        for t in msg.transforms:
            if t.header.frame_id == 'map' and t.child_frame_id == 'odom':
                p, q = t.transform.translation, t.transform.rotation
                latest['map_odom'] = [p.x, p.y, math.atan2(2*q.w*q.z, 1-2*q.z*q.z)]

    node.create_subscription(Odometry, '/odom', odom, 10)
    node.create_subscription(Twist, '/cmd_vel_safe', lambda m: latest.update(safe=[m.linear.x, m.angular.z]), 10)
    node.create_subscription(JointState, '/joint_states', lambda m: latest.update(wheels=dict(zip(m.name, m.velocity))), 10)
    node.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', lambda m: latest.update(covariance=[m.pose.covariance[i] for i in (0,7,35)]), latched)
    node.create_subscription(OccupancyGrid, '/map', lambda m: observations.update(map=m), latched)
    node.create_subscription(LaserScan, '/scan', lambda m: observations.update(scan=m), qos_profile_sensor_data)
    node.create_subscription(TFMessage, '/tf', tf, 10)
    node.create_subscription(Clock, '/clock', lambda m: latest.update(sim_seconds=m.clock.sec+m.clock.nanosec/1e9), qos_profile_sensor_data)
    deadline = time.monotonic()+30
    while not all(k in latest for k in ('odom', 'safe', 'wheels')):
        rclpy.spin_once(node, timeout_sec=0.1)
        if time.monotonic() > deadline:
            raise RuntimeError('Missing stationary sampling topics')
    settle_end = time.monotonic()+args.settle
    while time.monotonic() < settle_end:
        rclpy.spin_once(node, timeout_sec=0.1)
    start = time.monotonic()
    rows = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w') as f:
        next_sample = start
        while time.monotonic()-start < args.seconds:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.monotonic()
            if now >= next_sample:
                row = {'seconds': now-start, **latest}
                f.write(json.dumps(row)+'\n')
                f.flush()
                rows.append(row)
                next_sample = now+1
    first, last = rows[0]['odom'], rows[-1]['odom']
    dx, dy = last[0]-first[0], last[1]-first[1]
    result = {'samples': len(rows), 'duration': rows[-1]['seconds'], 'displacement_m': math.hypot(dx,dy), 'yaw_change_rad': last[2]-first[2], 'body_forward_m': math.cos(first[2])*dx+math.sin(first[2])*dy, 'body_lateral_m': -math.sin(first[2])*dx+math.cos(first[2])*dy, 'max_wheel_rad_s': max(abs(v) for row in rows for v in row['wheels'].values()), 'max_safe_command': max(abs(v) for row in rows for v in row['safe'])}
    result['max_displacement_m'] = max(math.hypot(row['odom'][0]-first[0], row['odom'][1]-first[1]) for row in rows)
    result['max_yaw_change_rad'] = max(abs(row['odom'][2]-first[2]) for row in rows)
    transforms = [row['map_odom'] for row in rows if 'map_odom' in row]
    if transforms:
        result['map_odom_excursion_m'] = max(math.hypot(t[0]-transforms[0][0],t[1]-transforms[0][1]) for t in transforms)
        result['map_odom_yaw_excursion_rad'] = max(abs(t[2]-transforms[0][2]) for t in transforms)
    if 'covariance' in latest:
        result['final_covariance'] = latest['covariance']
    if 'sim_seconds' in rows[0] and 'sim_seconds' in rows[-1]:
        result['sim_duration'] = rows[-1]['sim_seconds']-rows[0]['sim_seconds']
    if all(k in observations for k in ('map','scan')):
        import numpy as np
        scan, grid = observations['scan'], observations['map']
        transform = buffer.lookup_transform('map', scan.header.frame_id, rclpy.time.Time())
        p, q = transform.transform.translation, transform.transform.rotation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        occupied = np.argwhere(np.array(grid.data).reshape(grid.info.height,grid.info.width) >= 65)
        occupied_xy = np.column_stack((occupied[:,1],occupied[:,0]))*grid.info.resolution + np.array([grid.info.origin.position.x,grid.info.origin.position.y])+grid.info.resolution/2
        distances = []
        for i, distance in enumerate(scan.ranges):
            if math.isfinite(distance) and scan.range_min < distance < scan.range_max-0.05:
                angle = yaw+scan.angle_min+i*scan.angle_increment
                endpoint = np.array([p.x+distance*math.cos(angle),p.y+distance*math.sin(angle)])
                distances.append(float(np.min(np.linalg.norm(occupied_xy-endpoint,axis=1))))
        if distances:
            result['scan_endpoint_count'] = len(distances)
            result['scan_wall_median_m'] = float(np.median(distances))
            result['scan_wall_fraction_within_0_1m'] = sum(d <= 0.1 for d in distances)/len(distances)
    args.output.with_suffix('.summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result, indent=2))
    node.destroy_node()
    rclpy.shutdown()
    if result['max_safe_command'] != 0:
        raise RuntimeError('Nonzero command invalidates stationary measurement')


if __name__ == '__main__':
    main()
