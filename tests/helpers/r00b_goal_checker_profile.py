"""Apply and read back the reversible R00-B goal-checker evaluation profile."""
import argparse
import json
import time
from pathlib import Path

import rclpy
import yaml
from action_msgs.msg import GoalStatusArray
from rcl_interfaces.srv import GetParameters, SetParameters
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, DurabilityPolicy


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--restore',type=Path)
    parser.add_argument('--profile',type=Path,help='Explicit isolated controller parameter profile')
    parser.add_argument('--node',default='/controller_server',help='Explicit parameter service node')
    args=parser.parse_args()
    rclpy.init(); node=rclpy.create_node('r00b_goal_checker_profile')
    states=[]; data={'passed':False,'node':args.node}
    node.create_subscription(GoalStatusArray,'/follow_path/_action/status',
        lambda m: states.extend(s.status for s in m.status_list),
        QoSProfile(depth=10,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    def call(kind,name,request):
        c=node.create_client(kind,name)
        try:
            if not c.wait_for_service(timeout_sec=10):raise TimeoutError(name)
            f=c.call_async(request);rclpy.spin_until_future_complete(node,f,timeout_sec=10)
            if not f.done() or f.result() is None:raise TimeoutError(name)
            return f.result()
        finally:node.destroy_client(c)
    try:
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.1)
        if any(s in (1,2,3) for s in states):raise RuntimeError('Active/pending navigation: refusing parameter changes')
        if args.restore:
            values=json.loads(args.restore.read_text())['before']
        else:
            profile=args.profile or Path(__file__).resolve().parents[2]/'config/waypoint_navigation_r00b_eval.yaml'
            values=yaml.safe_load(profile.read_text())[args.node.split('/')[-1]]['ros__parameters']
        names=list(values)
        def read():
            answer=call(GetParameters,args.node+'/get_parameters',GetParameters.Request(names=names))
            def decode(v):
                if v.type==1:return v.bool_value
                if v.type==3:return v.double_value
                if v.type==4:return v.string_value
                raise RuntimeError('Unsupported parameter type: '+str(v.type))
            return {name:decode(v) for name,v in zip(names,answer.values)}
        data['before']=read();data['requested']=values
        parameters=[Parameter(name,value=value).to_parameter_msg() for name,value in values.items()]
        answer=call(SetParameters,args.node+'/set_parameters',SetParameters.Request(parameters=parameters))
        data['results']=[{'successful':v.successful,'reason':v.reason} for v in answer.results]
        if not all(v.successful for v in answer.results):raise RuntimeError('Parameter rejection')
        data['after']=read()
        if data['after']!=values:raise RuntimeError('Readback mismatch')
        data['passed']=True
    except Exception as error:data['error']=repr(error)
    finally:
        node.destroy_node();rclpy.shutdown();args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data),flush=True)
    return 0 if data['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
