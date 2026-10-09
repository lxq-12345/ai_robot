"""Minimal R00-B evaluation client; no velocity publisher or production app."""
import argparse
import copy
import json
import math
import time
from pathlib import Path

import rclpy
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from rclpy.time import Time
from nav2_msgs.action import ComputePathThroughPoses, FollowPath
from nav2_simple_commander.robot_navigator import BasicNavigator
from nav_msgs.msg import Path as PathMessage
from geometry_msgs.msg import PoseStamped, Twist
from tf2_ros import Buffer, TransformListener


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--route', choices=['A', 'B'], required=True)
    ap.add_argument('--scenario', choices=['open', 'turn', 'cancel', 'unreachable', 'input', 'unavailable', 'wall', 'reverse'], required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--gui', action='store_true')
    ap.add_argument('--gui-button-y', type=int, default=199, help='Measured Clear/Publish button row in the owned RViz layout')
    ap.add_argument('--latest-path-transforms', action='store_true', help='Resolve map geometry against current TF during execution; retain original plan timestamp in evidence')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    n = rclpy.create_node('r00b_observer_' + args.route.lower(), parameter_overrides=[Parameter('use_sim_time', value=True)])
    tf = Buffer()
    listener = TransformListener(tf, n)
    messages, trace, velocities = [], [], []
    data = {'route': args.route, 'scenario': args.scenario, 'passed': False, 'targets': [],
            'method': 'isolated evaluation prototype', 'gui_button_y': args.gui_button_y, 'thresholds': {'waypoint_m': 0.30, 'end_m': 0.25, 'end_rad': 0.25}, 'events': []}
    nav = None
    active = None
    clients = []
    pose_log = (args.output / 'trajectory.jsonl').open('w')
    def event(name, **detail):
        item = {'event': name, 't': time.monotonic(), **detail}
        data['events'].append(item)
        print(json.dumps(item), flush=True)
    def sample():
        if not tf.can_transform('map', 'base_footprint', Time()):
            return
        t = tf.lookup_transform('map', 'base_footprint', Time()).transform
        q = t.rotation
        item = {'t': time.monotonic(), 'ros_s': n.get_clock().now().nanoseconds / 1e9,
                'x': t.translation.x, 'y': t.translation.y,
                'yaw': math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))}
        for parent, child, key in [('odom', 'base_footprint', 'odom_pose'), ('map', 'odom', 'map_odom')]:
            if tf.can_transform(parent, child, Time()):
                v=tf.lookup_transform(parent, child, Time())
                z=v.transform.rotation
                item[key]={'x':v.transform.translation.x,'y':v.transform.translation.y,
                    'yaw':math.atan2(2*(z.w*z.z+z.x*z.y),1-2*(z.y*z.y+z.z*z.z)),
                    'stamp_s':v.header.stamp.sec+v.header.stamp.nanosec/1e9}
        trace.append(item)
        pose_log.write(json.dumps(item)+'\n')
    n.create_subscription(PathMessage, '/waypoint_path', lambda m: messages.append(m), 10)
    n.create_subscription(Twist, '/cmd_vel_safe', lambda m: velocities.append({'t':time.monotonic(),'v':m.linear.x,'w':m.angular.z}), 10)
    n.create_timer(0.1, sample)
    pub = n.create_publisher(PathMessage, '/r00b/' + args.route.lower() + '/prepared_path', 10)
    def until(fn, seconds=20):
        end = time.monotonic()+seconds
        while time.monotonic()<end:
            rclpy.spin_once(n, timeout_sec=0.03)
            if fn():return
        raise TimeoutError('deadline waiting for '+str(fn))
    def observe(seconds):
        end=time.monotonic()+seconds
        until(lambda:time.monotonic()>=end,seconds+1)
    def future(f, seconds=20):
        until(f.done, seconds)
        if f.exception():raise f.exception()
        return f.result()
    def goal(x,y,heading=0):
        p=PoseStamped();p.header.frame_id='map';p.header.stamp=n.get_clock().now().to_msg()
        p.pose.position.x=float(x);p.pose.position.y=float(y)
        p.pose.orientation.z=math.sin(heading/2);p.pose.orientation.w=math.cos(heading/2)
        return p
    try:
        until(lambda:bool(trace))
        data['initial_pose']=trace[-1]
        if args.scenario=='unavailable':
            for typ,name in [(ComputePathThroughPoses,'compute_path_through_poses'),(FollowPath,'follow_path')]:
                c=ActionClient(n,typ,'/r00b/nonexistent/'+name);clients.append(c)
                start=time.monotonic(); ready=c.wait_for_server(timeout_sec=2)
                event('missing_server', action=name, ready=ready, duration=time.monotonic()-start)
                assert not ready
            data['passed']=True
        else:
            if args.scenario=='cancel':
                xy=[(2.6,4.8),(2.6,5.5)]
            elif args.scenario in ['open','input']:
                xy=[(2.2,4.0),(2.6,4.0)]
            elif args.scenario=='turn':xy=[(2.6,4.8),(2.6,5.5 if args.route=='A' else 4.0)]
            elif args.scenario=='wall':xy=[(3.5,5.0),(4.2,5.0)]
            elif args.scenario=='reverse':xy=[(2.2,4.0),(1.8,4.0)]
            else:xy=[(2.2,4.0),(-20.0,-20.0)]
            goals=[goal(x,y,math.pi/2 if args.scenario=='turn' else 0) for x,y in xy]
            if args.gui:
                from r00b_rviz_input import RvizInput
                gui=RvizInput(Path(__file__).resolve().parents[2])
                gui.click(90,args.gui_button_y)  # Clear only the owned evaluation waypoints.
                for x,y in xy:gui.waypoint(x,y)
                gui.click(370,args.gui_button_y)
                until(lambda:bool(messages),8)
                goals=messages[-1].poses
                event('rviz_input', frame=messages[-1].header.frame_id,points=[(p.pose.position.x,p.pose.position.y) for p in goals])
                assert len(goals)==2, 'Expected exactly two RViz waypoints'
                assert messages[-1].header.frame_id=='map'
                for p in goals:
                    if not p.header.frame_id:
                        p.header.frame_id=messages[-1].header.frame_id
                    p.header.stamp=messages[-1].header.stamp
                event('thin_adapter', rule='inherit parent Path header for empty pose headers')
            else:event('synthetic_input',note='Action backend evaluation; does not prove RViz integration')
            data['goals']=[{'x':p.pose.position.x,'y':p.pose.position.y,'yaw':2*math.atan2(p.pose.orientation.z,p.pose.orientation.w)} for p in goals]
            observe(2)
            event('input_only_no_local_action',targets=len(data['targets']))
            if args.scenario=='input':
                assert all(abs(v['v'])<0.001 and abs(v['w'])<0.001 for v in velocities[-20:])
                data['passed']=True
            else:
                event('manual_plan')
                start=time.monotonic()
                if args.route=='A':
                    c=ActionClient(n,ComputePathThroughPoses,'/compute_path_through_poses');clients.append(c)
                    assert c.wait_for_server(timeout_sec=10)
                    req=ComputePathThroughPoses.Goal();req.goals=goals;req.planner_id='GridBased';req.use_start=False
                    h=future(c.send_goal_async(req));assert h.accepted
                    data['targets'].append({'kind':'plan','uuid':bytes(h.goal_id.uuid).hex()})
                    result=future(h.get_result_async());status=result.status;path=result.result.path
                else:
                    nav=BasicNavigator(node_name='r00b_commander');nav.set_parameters([Parameter('use_sim_time',value=True)])
                    # Observe on a separate node while Commander spins its own node.
                    from rclpy.executors import SingleThreadedExecutor
                    import threading
                    executor=SingleThreadedExecutor();executor.add_node(n)
                    worker=threading.Thread(target=executor.spin,daemon=True);worker.start()
                    path=nav.getPathThroughPoses(goal(trace[-1]['x'],trace[-1]['y']),goals,planner_id='GridBased',use_start=False)
                    status=nav.status
                    if nav.goal_handle:data['targets'].append({'kind':'plan','uuid':bytes(nav.goal_handle.goal_id.uuid).hex()})
                    executor.shutdown();worker.join(timeout=2);executor.remove_node(n)
                event('plan_result',status=status,duration=time.monotonic()-start,poses=len(path.poses) if path else 0)
                if args.scenario=='unreachable':
                    assert status!=4 or not path or not path.poses
                    data['passed']=True
                else:
                    assert status==4 and path and path.poses,'Planning failed'
                    data['planned_path']={'frame':path.header.frame_id,
                        'stamp_s':path.header.stamp.sec+path.header.stamp.nanosec/1e9,
                        'poses':[{'x':p.pose.position.x,'y':p.pose.position.y,
                            'yaw':2*math.atan2(p.pose.orientation.z,p.pose.orientation.w),
                            'frame':p.header.frame_id,'stamp_s':p.header.stamp.sec+p.header.stamp.nanosec/1e9} for p in path.poses]}
                    event('path_end', **data['planned_path']['poses'][-1])
                    execution_path=copy.deepcopy(path)
                    if args.latest_path_transforms:
                        # Humble ControllerServer retains the last pose timestamp.
                        # Map geometry stays fixed; transformation to local odom must
                        # follow current localization, not the planning-time transform.
                        for p in execution_path.poses:
                            p.header.stamp.sec=0;p.header.stamp.nanosec=0
                        event('execution_transform_policy', policy='latest TF for poses; original plan age retained', plan_stamp_s=data['planned_path']['stamp_s'])
                    pub.publish(path)
                    event('preview_no_execute',targets=len(data['targets']))
                    observe(2)
                    event('manual_execute'); start=time.monotonic();trace_start=len(trace)
                    if args.route=='A':
                        c=ActionClient(n,FollowPath,'/follow_path');clients.append(c)
                        assert c.wait_for_server(timeout_sec=10)
                        req=FollowPath.Goal();req.path=execution_path;req.controller_id='FollowPath';req.goal_checker_id='general_goal_checker'
                        active=future(c.send_goal_async(req));assert active.accepted
                        data['targets'].append({'kind':'execute','uuid':bytes(active.goal_id.uuid).hex()})
                        rf=active.get_result_async()
                        if args.scenario=='cancel':
                            until(lambda:time.monotonic()-start>1 or any(abs(v['v'])>.03 for v in velocities if v['t']>start),5)
                            event('cancel_precondition', moving=any(abs(v['v'])>.03 or abs(v['w'])>.05 for v in velocities if v['t']>start))
                            cancel_t=time.monotonic();cr=future(active.cancel_goal_async());event('cancel_reply',return_code=cr.return_code,count=len(cr.goals_canceling))
                            assert cr.goals_canceling
                        result=future(rf,100);status=result.status;active=None
                    else:
                        assert nav.followPath(execution_path,controller_id='FollowPath',goal_checker_id='general_goal_checker')
                        data['targets'].append({'kind':'execute','uuid':bytes(nav.goal_handle.goal_id.uuid).hex()})
                        if args.scenario=='cancel':
                            until(lambda:time.monotonic()-start>1 or any(abs(v['v'])>.03 for v in velocities if v['t']>start),5)
                            event('cancel_precondition', moving=any(abs(v['v'])>.03 or abs(v['w'])>.05 for v in velocities if v['t']>start))
                            cancel_t=time.monotonic();nav.cancelTask();event('cancel_reply',note='Commander API returns no cancellation response')
                        until(lambda:nav.isTaskComplete(),100);status=nav.status
                    event('execute_result',status=status,duration=time.monotonic()-start)
                    sample()
                    data['terminal_pose']=trace[-1]
                    observe(1)
                    data['end_pose']=trace[-1]
                    data['max_displacement_m']=max(math.hypot(t['x']-trace[trace_start]['x'],t['y']-trace[trace_start]['y']) for t in trace[trace_start:])
                    distances=[];index=trace_start
                    for p in goals:
                        candidates=trace[index:]
                        distances.append(min(math.hypot(t['x']-p.pose.position.x,t['y']-p.pose.position.y) for t in candidates) if candidates else None)
                        hit=next((j for j in range(index,len(trace)) if math.hypot(trace[j]['x']-p.pose.position.x,trace[j]['y']-p.pose.position.y)<=.30),None)
                        if hit is not None:index=hit+1
                    data['minimum_distances_m']=distances
                    data['last_velocities']=velocities[-10:]
                    if args.scenario=='cancel':
                        data['cancel_to_terminal_and_observation_s']=time.monotonic()-cancel_t
                        assert status==5 and all(abs(v['v'])<.01 and abs(v['w'])<.01 for v in velocities[-5:])
                    else:
                        end=goals[-1]; d=math.hypot(trace[-1]['x']-end.pose.position.x,trace[-1]['y']-end.pose.position.y)
                        yaw=2*math.atan2(end.pose.orientation.z,end.pose.orientation.w)
                        error=abs(math.atan2(math.sin(trace[-1]['yaw']-yaw),math.cos(trace[-1]['yaw']-yaw)))
                        data['end_error']={'position_m':d,'yaw_rad':error}
                        assert data['max_displacement_m']>.05, 'No meaningful motion; insufficient navigation evidence'
                        assert status==4 and all(x is not None and x<=.30 for x in distances) and d<=.25 and error<=.25
                    data['passed']=True
    except (Exception, KeyboardInterrupt) as ex:
        data['error']=repr(ex);event('exception',error=repr(ex))
        if active:
            try:future(active.cancel_goal_async(),5)
            except Exception:pass
        if nav and nav.result_future and not nav.result_future.done():
            try:nav.cancelTask()
            except Exception:pass
    finally:
        data['waypoint_messages']=len(messages)
        data['trace_samples']=len(trace)
        pose_log.close()
        for c in clients:c.destroy()
        if nav:nav.destroy_node()
        n.destroy_node();rclpy.shutdown()
        (args.output/'result.json').write_text(json.dumps(data,indent=2)+'\n')
    return 0 if data['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
