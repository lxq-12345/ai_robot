"""Read-only U01 checks against a running Gazebo/Nav2 session; never send goals."""

import argparse
import json
import time
from pathlib import Path

import rclpy
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import (
    ComputePathThroughPoses,
    ComputePathToPose,
    FollowPath,
    NavigateThroughPoses,
    NavigateToPose,
)
from rcl_interfaces.srv import GetParameters
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.parameter import Parameter
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = []
    rclpy.init()
    node = rclpy.create_node(
        'u01_readiness_probe',
        parameter_overrides=[Parameter('use_sim_time', value=True)],
    )
    buffer = Buffer(cache_time=Duration(seconds=10))
    listener = TransformListener(buffer, node)
    passed = False

    def record(check, ok, detail):
        results.append({'check': check, 'passed': bool(ok), 'detail': detail})
        print(json.dumps(results[-1]), flush=True)
        if not ok:
            raise RuntimeError(check)

    def request(service, service_type, message):
        client = node.create_client(service_type, service)
        try:
            if not client.wait_for_service(timeout_sec=20):
                raise RuntimeError('Service unavailable: ' + service)
            future = client.call_async(message)
            rclpy.spin_until_future_complete(node, future, timeout_sec=20)
            if not future.done() or future.result() is None:
                raise RuntimeError('Service response timeout: ' + service)
            return future.result()
        finally:
            node.destroy_client(client)

    try:
        for name in ['planner_server', 'controller_server', 'amcl', 'map_server']:
            response = request('/' + name + '/get_state', GetState, GetState.Request())
            record('lifecycle:' + name, response.current_state.id == 3,
                   {'id': response.current_state.id, 'label': response.current_state.label})
        for name in ['planner_server', 'controller_server', 'amcl', 'map_server',
                     'velocity_smoother', 'rviz', 'robot_state_publisher', 'gazebo']:
            response = request('/' + name + '/get_parameters', GetParameters,
                               GetParameters.Request(names=['use_sim_time']))
            value = response.values[0]
            record('clock:' + name, value.type == 1 and value.bool_value,
                   {'type': value.type, 'value': value.bool_value})
        for name, action_type in [
            ('compute_path_through_poses', ComputePathThroughPoses),
            ('compute_path_to_pose', ComputePathToPose), ('follow_path', FollowPath),
            ('navigate_to_pose', NavigateToPose), ('navigate_through_poses', NavigateThroughPoses),
        ]:
            client = ActionClient(node, action_type, '/' + name)
            try:
                ready = client.wait_for_server(timeout_sec=20)
                record('action:' + name, ready, {'server_ready': ready})
            finally:
                client.destroy()
        for parent, child in [('map', 'base_footprint'), ('base_footprint', 'base_link'),
                              ('base_link', 'laser_link')]:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=0.1)
                if buffer.can_transform(parent, child, Time()):
                    break
            valid = buffer.can_transform(parent, child, Time())
            detail = {'parent': parent, 'child': child}
            if valid:
                transform = buffer.lookup_transform(parent, child, Time())
                detail['stamp_s'] = transform.header.stamp.sec + transform.header.stamp.nanosec / 1e9
                detail['translation'] = [transform.transform.translation.x,
                                         transform.transform.translation.y,
                                         transform.transform.translation.z]
            record('tf:' + parent + '->' + child, valid, detail)
        record('sim_clock', node.get_clock().now().nanoseconds > 0,
               {'now_s': node.get_clock().now().nanoseconds / 1e9})
        for topic in ['/cmd_vel_raw', '/cmd_vel', '/cmd_vel_safe', '/waypoint_path',
                      '/particle_cloud']:
            publishers = node.get_publishers_info_by_topic(topic)
            subscribers = node.get_subscriptions_info_by_topic(topic)
            def endpoints(items):
                return [{'node': i.node_name, 'type': i.topic_type,
                         'reliability': i.qos_profile.reliability.name,
                         'durability': i.qos_profile.durability.name} for i in items]
            detail = {'publishers': endpoints(publishers), 'subscribers': endpoints(subscribers)}
            valid = bool(publishers)
            if topic == '/cmd_vel_safe':
                valid = len(publishers) == 1 and publishers[0].node_name == 'cmd_vel_guard'
                valid = valid and any(i.node_name == 'ai_robot_diff_drive' for i in subscribers)
            record('topic:' + topic, valid, detail)
        passed = True
    except Exception as error:
        results.append({'check': 'exception', 'passed': False, 'detail': str(error)})
        print(str(error), flush=True)
    finally:
        del listener
        node.destroy_node()
        rclpy.shutdown()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'passed': passed, 'checks': results}, indent=2) + '\n')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
