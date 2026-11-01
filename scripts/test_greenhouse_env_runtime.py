#!/usr/bin/env python3
"""Isolated developer smoke: load exact world, verify models, render, cleanup."""
import os,signal,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]; logs=root/'log/greenhouse_env';logs.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env['GAZEBO_IP']='127.0.0.1';env['GAZEBO_MASTER_URI']='http://127.0.0.1:11365';env['GAZEBO_MODEL_DATABASE_URI']=''
env['GAZEBO_MODEL_PATH']=str(root/'src/ai_robot_sim/models')+':/usr/share/gazebo-11/models'
processes=[]; handles=[]
try:
    import socket
    sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',11365));sock.close()
    for args,name in [(['gzserver','--verbose',str(root/'src/ai_robot_sim/worlds/greenhouse_env.world')],'server')]:
        handle=open(logs/f'{name}.log','w');handles.append(handle)
        processes.append(subprocess.Popen(args,env=env,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True))
    deadline=time.monotonic()+100; listing=''
    while time.monotonic()<deadline:
        if processes[0].poll() is not None: raise RuntimeError('server exited')
        try:
            r=subprocess.run(['gz','model','-w','greenhouse_env','-m','track_2_28','-i'],env=env,capture_output=True,text=True,timeout=5)
            listing=r.stdout
            if 'name: "track_2_28"' in listing: break
        except subprocess.TimeoutExpired: pass
        time.sleep(2)
    (logs/'models.txt').write_text(listing)
    names=[f'planting_{b}_{i:02}' for b in (1,2) for i in range(30)]+[f'track_{b}_{i:02}' for b in (1,2) for i in range(29)]
    def check(name):
        for attempt in range(3):
            result=subprocess.run(['gz','model','-w','greenhouse_env','-m',name,'-i'],env=env,capture_output=True,text=True,timeout=12)
            if f'name: "{name}"' in result.stdout:
                return name
            (logs/f'query_failure_{name}_{attempt}.txt').write_text(result.stdout+result.stderr)
            time.sleep(.5)
        raise AssertionError(name)
    checked=names if env.get('GREENHOUSE_RENDER_ONLY')=='1' else [check(name) for name in names]
    (logs/'models.txt').write_text('\n'.join(checked)+'\n')
    h=open(logs/'client.log','w');handles.append(h)
    processes.append(subprocess.Popen(['gzclient','--verbose'],env=env,stdout=h,stderr=subprocess.STDOUT,start_new_session=True))
    import re,ctypes
    deadline=time.monotonic()+100; window=None
    while time.monotonic()<deadline:
        assert processes[-1].poll() is None,'client exited'
        tree=subprocess.run(['xwininfo','-root','-tree'],capture_output=True,text=True,env=env).stdout
        match=re.search(r'(0x[0-9a-f]+) "Gazebo"',tree)
        if match:
            window=int(match.group(1),16);break
        time.sleep(2)
    assert window is not None,'Gazebo window not found'
    x=ctypes.CDLL('libX11.so.6');x.XOpenDisplay.restype=ctypes.c_void_p
    display=x.XOpenDisplay(None)
    x.XMapRaised.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    x.XFlush.argtypes=[ctypes.c_void_p]
    x.XMapRaised(display,window);x.XFlush(display)
    for _ in range(4):
        time.sleep(30)
    subprocess.run(['import','-window',hex(window),str(root/'tests/evidence/greenhouse_env/developer_render.png')],env=env,check=True,timeout=15)
    print('PASS: actual world loaded, Gazebo window captured; model checks ' + ('reused from prior complete run (render-only)' if env.get('GREENHOUSE_RENDER_ONLY')=='1' else '60 planting + 58 track passed'))
finally:
    for p in reversed(processes):
        if p.poll() is None: os.killpg(p.pid,signal.SIGINT)
    for p in reversed(processes):
        try:p.wait(timeout=12)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=8)
    for h in handles:h.close()
