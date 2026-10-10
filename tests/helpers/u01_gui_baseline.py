"""Exercise the existing RViz UI and measure U01; no velocity publisher."""

import argparse
import ctypes
import json
import math
import re
import subprocess
import time
from pathlib import Path

import rclpy
import yaml
from action_msgs.msg import GoalStatusArray
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import ComputePathThroughPoses, NavigateToPose
from nav_msgs.msg import Path as PathMessage
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener
from unique_identifier_msgs.msg import UUID


def yaw(quaternion):
    return math.atan2(2 * (quaternion.w * quaternion.z + quaternion.x * quaternion.y),
                      1 - 2 * (quaternion.y ** 2 + quaternion.z ** 2))


from r00b_rviz_input import RvizInput as OwnedRvizInput

class RvizInput(OwnedRvizInput):
    def __init__(self, workspace, height):
        super().__init__(workspace, required_size=(1500, height))

    def goal(self, x, y, heading):
        self.click(self.goal_button_x, 40)
        self.move(*self.point(x, y))
        self.button(True)
        try:
            self.move(*self.point(x + .35 * math.cos(heading), y + .35 * math.sin(heading)))
        finally:
            self.button(False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument("--window-height", type=int, required=True)
    parser.add_argument("--button-y", type=int, required=True)
    parser.add_argument("--goal-button-x", type=int, required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    args.output.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = rclpy.create_node('u01_gui_baseline', parameter_overrides=[Parameter('use_sim_time', value=True)])
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    gui = RvizInput(workspace, args.window_height)
    gui.goal_button_x = args.goal_button_x
    data = {'passed': False, 'method': 'AI-operated real RViz GUI integration; not learner manual practice',
            'results': [], 'goal_messages': [], 'waypoint_messages': [], 'planning_goal_ids': []}
    safe, statuses, latest_trace = [], {}, []
    trace_file = (args.output / 'trajectory.jsonl').open('w')
    current_goal = None

    def pose():
        t = buffer.lookup_transform('map', 'base_footprint', Time())
        return [t.transform.translation.x, t.transform.translation.y, yaw(t.transform.rotation)]

    def sample():
        if not buffer.can_transform('map', 'base_footprint', Time()):
            return
        item = {'monotonic': time.monotonic(), 'ros_s': node.get_clock().now().nanoseconds / 1e9,
                'map_pose': pose()}
        latest_trace.append(item)
        trace_file.write(json.dumps(item) + '\n')

    def goal_message(message):
        data['goal_messages'].append({'received': time.monotonic(), 'frame': message.header.frame_id,
                                     'x': message.pose.position.x, 'y': message.pose.position.y,
                                     'yaw': yaw(message.pose.orientation)})

    def waypoints(message):
        data['waypoint_messages'].append({'received': time.monotonic(), 'frame': message.header.frame_id,
            'stamp_s': message.header.stamp.sec + message.header.stamp.nanosec / 1e9,
            'poses': [{'frame': p.header.frame_id,
                       'position': [p.pose.position.x, p.pose.position.y, p.pose.position.z],
                       'quaternion': [p.pose.orientation.x, p.pose.orientation.y,
                                      p.pose.orientation.z, p.pose.orientation.w]} for p in message.poses]})

    def status_message(message):
        for s in message.status_list:
            statuses[bytes(s.goal_info.goal_id.uuid).hex()] = s.status

    node.create_subscription(PoseStamped, '/goal_pose', goal_message, 10)
    node.create_subscription(PathMessage, '/waypoint_path', waypoints, 10)
    node.create_subscription(Twist, '/cmd_vel_safe',
        lambda m: safe.append({'t': time.monotonic(), 'linear': m.linear.x, 'angular': m.angular.z}), 10)
    node.create_subscription(GoalStatusArray, '/navigate_to_pose/_action/status', status_message, 10)
    node.create_subscription(GoalStatusArray, '/compute_path_through_poses/_action/status',
        lambda m: data['planning_goal_ids'].extend(bytes(s.goal_info.goal_id.uuid).hex() for s in m.status_list), 10)
    node.create_timer(0.10, sample)

    def spin_until(condition, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if condition():
                return
        raise RuntimeError('Observation timed out')

    def observe(seconds):
        end = time.monotonic() + seconds
        spin_until(lambda: time.monotonic() >= end, seconds + 1)

    def result_for(identifier):
        client = node.create_client(NavigateToPose.Impl.GetResultService, '/navigate_to_pose/_action/get_result')
        if not client.wait_for_service(timeout_sec=10):
            raise RuntimeError('Result service missing')
        request = NavigateToPose.Impl.GetResultService.Request(goal_id=UUID(uuid=list(bytes.fromhex(identifier))))
        return client, client.call_async(request)

    def gui_goal(x, y, heading):
        nonlocal current_goal
        previous = set(statuses)
        pixel = tuple(round(v) for v in gui.point(x, y))
        arrow = tuple(round(v) for v in gui.point(x + .35 * math.cos(heading), y + .35 * math.sin(heading)))
        angle, scale = gui.view['Angle'], gui.view['Scale']
        def map_point(point):
            dx = (point[0] - gui.canvas[2] - gui.canvas[0]/2) / scale
            dy = (point[1] - gui.canvas[3] - gui.canvas[1]/2) / scale
            return (gui.view['X'] + math.cos(angle)*dx + math.sin(angle)*dy,
                    gui.view['Y'] + math.sin(angle)*dx - math.cos(angle)*dy)
        actual, tip = map_point(pixel), map_point(arrow)
        requested = {'frame': 'map', 'x': actual[0], 'y': actual[1],
                     'yaw': math.atan2(tip[1]-actual[1], tip[0]-actual[0]),
                     'source': 'calibrated real Nav2 Goal mouse pixels', 'pixel': pixel, 'arrow_pixel': arrow}
        gui.goal(x, y, heading)
        spin_until(lambda: bool(set(statuses) - previous), 10)
        identifiers = set(statuses) - previous
        if len(identifiers) != 1:
            raise RuntimeError('Ambiguous GUI navigation goal IDs')
        current_goal = next(iter(identifiers))
        data['goal_messages'].append(requested)
        return requested, current_goal

    def cancel(identifier):
        client = node.create_client(CancelGoal, '/navigate_to_pose/_action/cancel_goal')
        if not client.wait_for_service(timeout_sec=10):
            raise RuntimeError('Cancel service missing')
        future = client.call_async(CancelGoal.Request(goal_info=__import__('action_msgs.msg', fromlist=['GoalInfo']).GoalInfo(
            goal_id=UUID(uuid=list(bytes.fromhex(identifier))))))
        spin_until(future.done, 10)
        response = future.result()
        node.destroy_client(client)
        if not response or not response.goals_canceling:
            raise RuntimeError('Cancellation rejected')

    try:
        spin_until(lambda: buffer.can_transform('map', 'base_footprint', Time()), 15)
        observe(3)
        stationary_start = len(latest_trace)
        safe_start = len(safe)
        before_status = set(statuses)
        before_plans = set(data['planning_goal_ids'])
        gui.click(90, args.button_y)
        gui.waypoint(2.20, 4.00)
        gui.waypoint(2.60, 4.00)
        observe(2)
        if data['waypoint_messages']:
            raise RuntimeError('Waypoint creation published before Publish')
        gui.click(370, args.button_y)
        spin_until(lambda: bool(data['waypoint_messages']), 5)
        observe(3)
        message = data['waypoint_messages'][-1]
        if message['frame'] != 'map' or len(message['poses']) != 2:
            raise RuntimeError('Waypoint count/frame mismatch')
        for received, expected in zip(message['poses'], [(2.20, 4.00), (2.60, 4.00)]):
            if math.hypot(received['position'][0] - expected[0], received['position'][1] - expected[1]) > 0.03:
                raise RuntimeError('Waypoint order/coordinates mismatch')
            if abs(sum(q*q for q in received['quaternion']) - 1) > 1e-6:
                raise RuntimeError('Waypoint quaternion not normalized')
        if set(statuses) != before_status or set(data['planning_goal_ids']) != before_plans:
            raise RuntimeError('Waypoint Publish triggered an action')
        if any(abs(s['linear']) > 0.01 or abs(s['angular']) > 0.01 for s in safe[safe_start:]):
            raise RuntimeError('Waypoint Publish triggered motion')
        stationary = latest_trace[stationary_start:]
        origin = stationary[0]['map_pose']
        deviation = max(math.hypot(t['map_pose'][0]-origin[0], t['map_pose'][1]-origin[1]) for t in stationary)
        data['results'].append({'case': 'T01-03', 'passed': True, 'map_stationary_deviation_m': deviation,
                                'message': message, 'created_without_publish': True, 'publish_no_motion': True})
        print('T01-03 passed', flush=True)

        planner = ActionClient(node, ComputePathThroughPoses, '/compute_path_through_poses')
        if not planner.wait_for_server(timeout_sec=10):
            raise RuntimeError('Planner unavailable')
        planning = ComputePathThroughPoses.Goal(planner_id='GridBased', use_start=False)
        for x in [2.20, 2.60]:
            p = PoseStamped()
            p.header.frame_id = 'map'
            p.header.stamp = node.get_clock().now().to_msg()
            p.pose.position.x, p.pose.position.y, p.pose.orientation.w = x, 4.0, 1.0
            planning.goals.append(p)
        began = time.monotonic()
        future = planner.send_goal_async(planning)
        spin_until(future.done, 10)
        handle = future.result()
        if not handle.accepted:
            raise RuntimeError('Baseline plan rejected')
        future = handle.get_result_async()
        spin_until(future.done, 10)
        result = future.result()
        if result.status != 4 or not result.result.path.poses:
            raise RuntimeError('Baseline plan failed')
        data['planning_baseline'] = {'wall_s': time.monotonic()-began,
            'server_s': result.result.planning_time.sec + result.result.planning_time.nanosec/1e9,
            'path_poses': len(result.result.path.poses)}
        planner.destroy()

        for label, target in [('open_area', (2.20, 4.00, 0.0)), ('turn', (2.60, 4.80, math.pi/2))]:
            began = time.monotonic()
            requested, identifier = gui_goal(*target)
            client, future = result_for(identifier)
            spin_until(future.done, 120)
            result = future.result()
            node.destroy_client(client)
            if result.status != 4:
                raise RuntimeError('GUI navigation did not succeed: ' + label)
            observe(0.5)
            end = pose()
            distance = math.hypot(end[0]-requested['x'], end[1]-requested['y'])
            angle = abs(math.atan2(math.sin(end[2]-requested['yaw']), math.cos(end[2]-requested['yaw'])))
            if distance > 0.25 or angle > 0.25:
                raise RuntimeError('Goal error exceeds configured tolerance')
            data['results'].append({'case': 'T01-02', 'scene': label, 'passed': True,
                'goal': requested, 'goal_id': identifier, 'result_status': result.status,
                'final_map_pose': end, 'position_error_m': distance, 'yaw_error_rad': angle,
                'duration_s': time.monotonic()-began})
            current_goal = None
            print(label + ' navigation passed', flush=True)

        safe_start = len(safe)
        requested, identifier = gui_goal(1.80, 4.00, 0.0)
        spin_until(lambda: any(abs(s['linear']) > 0.03 for s in safe[safe_start:]), 30)
        requested_at = time.monotonic()
        cancel(identifier)
        acknowledged_at = time.monotonic()
        client, future = result_for(identifier)
        spin_until(future.done, 10)
        result_at = time.monotonic()
        result = future.result()
        node.destroy_client(client)
        if result.status != 5:
            raise RuntimeError('Goal cancellation not confirmed')
        observe(2)
        after = [s for s in safe if s['t'] >= requested_at]
        moving = [s['t'] for s in after if abs(s['linear']) > 0.01 or abs(s['angular']) > 0.01]
        stopped_at = next((s['t'] for s in after if s['t'] > max(moving, default=requested_at)), None)
        if stopped_at is None or stopped_at-requested_at > 2:
            raise RuntimeError('Cancellation stop too slow or unobserved')
        data['results'].append({'case': 'T01-04_cancel', 'passed': True,
            'goal_id': identifier, 'result_status': result.status,
            'ack_s': acknowledged_at-requested_at, 'terminal_s': result_at-requested_at,
            'stop_s': stopped_at-requested_at, 'observation_s': 2})
        current_goal = None
        print('Cancellation passed', flush=True)

        safe_start = len(safe)
        gui_goal(2.60, 4.00, 0.0)
        spin_until(lambda: any(abs(s['linear']) > 0.03 for s in safe[safe_start:]), 30)
        stopped_began = time.monotonic()
        with (args.output / 'independent_shutdown.log').open('w') as log:
            process = subprocess.Popen(['bash', str(workspace / 'scripts/stop_au9_manual_nav2.sh')], stdout=log, stderr=subprocess.STDOUT)
            spin_until(lambda: process.poll() is not None, 40)
        if process.returncode != 0:
            raise RuntimeError('Independent stop failed')
        data['results'].append({'case': 'T01-04_independent_stop', 'passed': True,
            'exit_code': process.returncode, 'duration_s': time.monotonic()-stopped_began,
            'safe_tail': safe[-10:]})
        current_goal = None
        data['passed'] = True
    except Exception as error:
        data['error'] = str(error)
        print('FAILED: ' + str(error), flush=True)
        if current_goal:
            try:
                cancel(current_goal)
            except Exception as cancel_error:
                data['cleanup_cancel_error'] = str(cancel_error)
    finally:
        data['safe_commands'] = safe
        data['status_snapshot'] = statuses
        trace_file.close()
        del listener
        node.destroy_node()
        rclpy.shutdown()
        (args.output / 'result.json').write_text(json.dumps(data, indent=2)+'\n')
    return 0 if data['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
