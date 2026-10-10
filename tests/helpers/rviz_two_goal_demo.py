"""Explicit two-goal RViz demo observer; GUI submits goals, no velocity publisher."""
import ctypes
import json
import math
import re
import subprocess
import time
from pathlib import Path
import yaml
import rclpy
from rclpy.parameter import Parameter
from rclpy.time import Time
from rclpy.qos import QoSProfile, DurabilityPolicy
from action_msgs.msg import GoalStatusArray
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import Twist
from nav_msgs.msg import Path as PathMessage
from tf2_ros import Buffer, TransformListener

out = Path('tests/evidence/waypoint_navigation/两航点完整演示_20261009')
rclpy.init()
node = rclpy.create_node('two_goal_demo_observer', parameter_overrides=[Parameter('use_sim_time', value=True)])
buffer = Buffer()
listener = TransformListener(buffer, node)
trace, velocities, events, paths, states = [], [], [], [], {}
def status(message):
    for item in message.status_list:
        key = bytes(item.goal_info.goal_id.uuid).hex()
        states[key] = item.status
        events.append({'id': key, 'status': item.status, 't': time.monotonic()})
node.create_subscription(GoalStatusArray, '/navigate_through_poses/_action/status', status,
                         QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL))
node.create_subscription(Twist, '/cmd_vel_safe', lambda m: velocities.append({'t':time.monotonic(),'v':m.linear.x,'w':m.angular.z}), 10)
node.create_subscription(PathMessage, '/plan', lambda m: paths.append({'frame':m.header.frame_id,'count':len(m.poses)}), 10)
def observe(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=.05)
        if buffer.can_transform('map','base_footprint',Time()):
            t = buffer.lookup_transform('map','base_footprint',Time()).transform
            trace.append({'t':time.monotonic(),'x':t.translation.x,'y':t.translation.y})

line = next(l for l in subprocess.check_output(['xwininfo','-root','-tree'],text=True).splitlines() if ' - RViz' in l)
window = int(re.search('0x[0-9a-f]+',line).group(),16)
x = ctypes.CDLL('libX11.so.6'); xt = ctypes.CDLL('libXtst.so.6')
x.XOpenDisplay.restype=ctypes.c_void_p; display=x.XOpenDisplay(None)
for name,args in {'XRaiseWindow':[ctypes.c_void_p,ctypes.c_ulong], 'XSetInputFocus':[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong], 'XGrabServer':[ctypes.c_void_p], 'XUngrabServer':[ctypes.c_void_p], 'XFlush':[ctypes.c_void_p], 'XSync':[ctypes.c_void_p,ctypes.c_int]}.items():getattr(x,name).argtypes=args
xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
xt.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
x.XQueryTree.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),ctypes.POINTER(ctypes.c_uint)]
x.XQueryPointer.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_uint)]
frame=window
while True:
    root,parent=ctypes.c_ulong(),ctypes.c_ulong(); children=ctypes.POINTER(ctypes.c_ulong)(); count=ctypes.c_uint()
    x.XQueryTree(display,frame,ctypes.byref(root),ctypes.byref(parent),ctypes.byref(children),ctypes.byref(count))
    if parent.value==root.value or not parent.value:break
    frame=parent.value
geometry=re.compile(r'(\d+)x(\d+)[+-]\d+[+-]\d+\s+([+-]\d+)([+-]\d+)')
def positions():
    tree=subprocess.check_output(['xwininfo','-root','-tree'],text=True).splitlines()
    main=tuple(map(int,geometry.search(next(l for l in tree if f'{window:#x} ' in l)).groups()))
    canvas=tuple(map(int,geometry.search(next(l for l in tree if '"rviz2": ("rviz2" "rviz2")' in l)).groups()))
    if main[:2]!=(1500,900):raise RuntimeError('Unexpected RViz size')
    return main,canvas
view=yaml.safe_load(Path('config/rviz2/au9_nav2.rviz').read_text())['Visualization Manager']['Views']['Current']
def gesture(start,end=None):
    # Keep the GUI press/drag/release together; never leave a held mouse button.
    x.XGrabServer(display)
    try:
        x.XRaiseWindow(display,frame);x.XSetInputFocus(display,window,1,0)
        xt.XTestFakeMotionEvent(display,-1,round(start[0]),round(start[1]),0);x.XSync(display,0)
        rr,child=ctypes.c_ulong(),ctypes.c_ulong();rx,ry,wx,wy=ctypes.c_int(),ctypes.c_int(),ctypes.c_int(),ctypes.c_int();mask=ctypes.c_uint()
        x.XQueryPointer(display,root.value,ctypes.byref(rr),ctypes.byref(child),ctypes.byref(rx),ctypes.byref(ry),ctypes.byref(wx),ctypes.byref(wy),ctypes.byref(mask))
        if child.value!=frame:raise RuntimeError('Pointer is not over owned RViz')
        xt.XTestFakeButtonEvent(display,1,1,0)
        if end:xt.XTestFakeMotionEvent(display,-1,round(end[0]),round(end[1]),0)
        xt.XTestFakeButtonEvent(display,1,0,0);x.XSync(display,0)
    finally:
        xt.XTestFakeButtonEvent(display,1,0,0);x.XUngrabServer(display);x.XFlush(display)
    observe(.4)
def click(px,py):
    main,_=positions();gesture((main[2]+px,main[3]+py))
def point(px,py):
    _,canvas=positions();a,s=view['Angle'],view['Scale'];dx,dy=px-view['X'],py-view['Y']
    return (canvas[2]+canvas[0]/2+s*(math.cos(a)*dx+math.sin(a)*dy),canvas[3]+canvas[1]/2+s*(math.sin(a)*dx-math.cos(a)*dy))
result={'goals':[[2.2,4.8],[2.6,4.8]],'passed':False}
try:
    observe(2)
    if not trace:raise RuntimeError('No robot TF')
    click(100,199)
    for px,py in result['goals']:click(710,40);gesture(point(px,py))
    click(285,849)
    for px,py in result['goals']:click(600,40);gesture(point(px,py),point(px+.35,py))
    subprocess.run(['import','-window',hex(window),str(out/'prepared.png')],check=True)
    observe(1);before=set(states);origin=trace[-1];result['origin']=origin
    click(285,786);began=time.monotonic();goal_id=None
    while time.monotonic()-began<100:
        observe(.2);new=set(states)-before
        if new:
            goal_id=next(iter(new))
            if states[goal_id] in (4,5,6):break
        if goal_id is None and time.monotonic()-began>10:raise RuntimeError('No new GUI Action goal')
    result['goal_id']=goal_id;result['terminal_status']=states.get(goal_id)
    if result['terminal_status'] not in (4,5,6):raise RuntimeError('Navigation terminal timeout')
    observe(3)
    result['max_displacement_m']=max(math.hypot(t['x']-origin['x'],t['y']-origin['y']) for t in trace if t['t']>=began)
    result['end']=trace[-1]
    result['stopped']=len(velocities)>=5 and all(abs(v['v'])<.01 and abs(v['w'])<.01 for v in velocities[-5:])
    result['passed']=result['terminal_status']==4 and result['max_displacement_m']>.3 and result['stopped']
except Exception as error:
    result['error']=str(error)
    client=node.create_client(CancelGoal,'/navigate_through_poses/_action/cancel_goal')
    if client.wait_for_service(timeout_sec=2):
        future=client.call_async(CancelGoal.Request());observe(3)
finally:
    result.update(trace=trace,velocities=velocities,status_events=events,paths=paths)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    subprocess.run(['import','-window',hex(window),str(out/'result.png')])
    print({k:v for k,v in result.items() if k not in ['trace','velocities','status_events','paths']},flush=True)
    node.destroy_node();rclpy.shutdown()
